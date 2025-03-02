import os
import json
import time
import re
from typing import Optional, Dict, Any, List, Union
import httpx
from dotenv import load_dotenv
from .models import Tweet, User
from .exceptions import (
    TwitterPlatformError,
    InvalidInputError,
    RateLimitError,
    InsufficientCreditsError,
    TimeoutError,
    ApidancePlatformError,
    ApiKeyError,
    AuthTokenError,
)
from .utils import parse_markdown_to_richtext

load_dotenv()


class TwitterClient:
    """Client for interacting with Twitter API via Apidance."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.apidance.pro",
        max_retries: int = 10,
        initial_retry_delay: float = 1.0,
        max_retry_delay: float = 32.0,
        backoff_factor: float = 2.0,
    ):
        """Initialize the Twitter client.

        Args:
            api_key: Optional API key. If not provided, will be read from APIDANCE_API_KEY env var.
            base_url: Base URL for API requests
            max_retries: Maximum number of retry attempts for failed requests
            initial_retry_delay: Initial delay between retries in seconds
            max_retry_delay: Maximum delay between retries in seconds
            backoff_factor: Multiplicative factor for exponential backoff
        """
        self.api_key = api_key or os.getenv("APIDANCE_API_KEY")
        if not self.api_key:
            raise ApiKeyError(
                "API key must be provided either through constructor or APIDANCE_API_KEY environment variable"
            )

        # Check balance
        balance = self.check_balance()
        if int(balance) < 100:
            raise InsufficientCreditsError(
                f"Warning: Your API balance is low ({balance}). Please recharge your account."
            )

        self.base_url = base_url
        self.client = httpx.Client()
        self.headers = {
            "apikey": self.api_key,
            "Content-Type": "application/json",
        }

        # Retry related configuration
        self.max_retries = max_retries
        self.initial_retry_delay = initial_retry_delay
        self.max_retry_delay = max_retry_delay
        self.backoff_factor = backoff_factor

    def _calculate_retry_delay(self, attempt: int) -> float:
        """Calculate retry delay using exponential backoff algorithm.

        Args:
            attempt: Current retry attempt number

        Returns:
            Delay time in seconds for the next retry
        """
        delay = min(
            self.initial_retry_delay * (self.backoff_factor ** (attempt - 1)),
            self.max_retry_delay,
        )
        return delay

    def _should_retry(self, response: httpx.Response, attempt: int) -> bool:
        """Determine if a request should be retried.

        Args:
            response: API response
            attempt: Current retry attempt number

        Returns:
            Whether to retry the request

        Raises:
            RateLimitError: When rate limit is exceeded
            InsufficientCreditsError: When API credits are depleted
            AuthenticationError: When authentication fails
        """
        # If we've reached the maximum attempts, don't retry
        if attempt >= self.max_retries:
            return False

        # Try to parse the response as JSON
        response_data = None
        try:
            response_data = response.json()
        except json.JSONDecodeError:
            # JSON parse error might be temporary, allow retry
            return True

        # Handle Twitter-style errors (with "errors" array)
        if response_data is not None and "errors" in response_data:
            error = response_data["errors"][0]
            error_code = error.get("code")

            # Rate limit error
            if error_code == 88:
                if attempt == self.max_retries:
                    raise RateLimitError("Rate limit exceeded. Please try again later.")
                return True
            # Other Twitter platform errors
            elif error_code == 366:
                raise InvalidInputError(error.get("message", ""))
            elif error_code == 139:  # Tweet already favorited
                return False
            elif (
                error_code == 64
            ):  # Account is suspended and is not permitted to access this feature, retry
                return True
            else:
                raise TwitterPlatformError(error.get("message", ""))

        # Handle Apidance API style errors
        if response_data is not None and response_data.get("code", 0) > 0:
            msg = response_data.get("msg", "").lower()
            if "insufficient api counts" in msg:
                raise InsufficientCreditsError("Insufficient api credits")
            else:
                raise ApidancePlatformError(msg)

        # Handle local rate limiting
        if response.text == "local_rate_limited":
            return True

        # Handle specific error cases based on response data
        if "data" in response_data:
            return False

        return False

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make an API request with retry logic.

        Args:
            method: HTTP method
            endpoint: API endpoint
            **kwargs: Additional request parameters

        Returns:
            API response data

        Raises:
            AuthTokenError: When authentication token is invalid
            PremiumRequiredError: When Premium+ is required
            RateLimitError: When rate limit is exceeded
            InsufficientCreditsError: When API credits are depleted
            TimeoutError: When request times out
            ApidancePlatformError: When the platform returns other errors
        """
        url = f"{self.base_url}{endpoint}"

        # Process request parameters
        if "params" in kwargs and "variables" in kwargs["params"]:
            kwargs["params"]["variables"] = json.dumps(kwargs["params"]["variables"])

        # Set request headers
        headers = self.headers.copy()
        token = os.getenv("X_AUTH_TOKEN")
        # These endpoints need X_AUTH_TOKEN regardless of HTTP method
        auth_required_endpoints = [
            "/graphql/FollowersYouKnow",
            "/graphql/CreateTweet",
            "/graphql/CreateNoteTweet",
            "/graphql/FavoriteTweet",
        ]
        if endpoint in auth_required_endpoints:
            if token:
                if not re.match(r"^[0-9a-f]{40}$", token):
                    raise AuthTokenError(
                        f"Invalid AuthToken format. Expected 40 character hexadecimal string, got: {token}"
                    )
                headers["AuthToken"] = token

        # Specific exceptions that should not be retried
        fatal_exceptions = (
            AuthTokenError,
            InsufficientCreditsError,
            ApidancePlatformError,
        )

        # Error storage
        last_error = None

        # Retry loop
        for attempt in range(1, self.max_retries + 1):
            try:
                # Make the actual HTTP request
                response = self.client.request(
                    method, url, headers=headers, timeout=10, **kwargs
                )

                try:
                    # Check if retry is needed
                    if not self._should_retry(response, attempt):
                        return response.json()
                except fatal_exceptions:
                    # These are explicit errors that should not be retried
                    raise
                except RateLimitError:
                    # Rate limit errors are handled directly in _should_retry
                    if attempt == self.max_retries:
                        raise
                    # If we're not at max retries, _should_retry will return True to continue
                except Exception as e:
                    # Record other errors and continue retrying
                    last_error = e
                    break

                # Calculate delay for next retry
                delay = self._calculate_retry_delay(attempt)
                time.sleep(delay)

            except httpx.ConnectError as e:
                if attempt == self.max_retries:
                    raise TimeoutError(f"Connection error: {str(e)}") from e
                # For network errors before max_retries, try again
                last_error = e
                delay = self._calculate_retry_delay(attempt)
                time.sleep(delay)
            except Exception as e:
                # Catch any other unexpected errors
                if attempt == self.max_retries:
                    raise ApidancePlatformError(f"Unexpected error: {str(e)}") from e
                last_error = e
                delay = self._calculate_retry_delay(attempt)
                time.sleep(delay)

        # If all retries failed, raise the final error
        if last_error:
            raise last_error

    def check_balance(self) -> int:
        """Check the remaining balance for the API key.

        Returns:
            int: Remaining balance

        Note:
            Returns 0 if connection fails or API returns error
        """
        try:
            response = httpx.get(
                f"https://api.apidance.pro/key/{self.api_key}", timeout=5.0, verify=True
            )

            # Try to parse as JSON
            try:
                data = response.json()
                # If the response is a direct integer
                if isinstance(data, int):
                    return data
                # If the response is an error object
                if isinstance(data, dict) and data.get("code") == -1:
                    return 0
                # Any other JSON response, try to convert text to int
                return int(response.text)
            except (json.JSONDecodeError, ValueError):
                # If not valid JSON but has text, try parsing as int
                if response.text:
                    try:
                        return int(response.text)
                    except ValueError:
                        return 0
                return 0

        except (
            httpx.ConnectError,
            httpx.ConnectTimeout,
            httpx.ReadTimeout,
            httpx.HTTPError,
            httpx.HTTPStatusError,
        ) as e:
            # Log the error if needed
            print(f"Warning: Could not connect to API server: {e}")
            # Return 0 as default balance when unable to check
            return 0

    def search_timeline(
        self,
        query: str,
        product: str = "Latest",
        count: int = 40,
        include_promoted_content: bool = False,
    ) -> List[Tweet]:
        """Search Twitter timeline with pagination support.

        Args:
            query: Search query string
            product: Type of search results. One of: Top, Latest, People, Photos, Videos
            count: Number of results to return (default: 40, set to -1 for all available results)
            include_promoted_content: Whether to include promoted content (default: False)

        Returns:
            List of Tweet objects from search results
        """
        all_tweets = []
        cursor = None
        batch_size = 20  # Twitter API default batch size for search

        while True:
            variables = {
                "rawQuery": query,
                "count": batch_size,
                "cursor": cursor,
                "querySource": "typed_query",
                "product": product,
                "includePromotedContent": include_promoted_content,
            }

            response = self._make_request(
                "GET",
                "/graphql/SearchTimeline",
                params={"variables": variables},
            )

            # Extract tweets from response
            timeline = (
                response.get("data", {})
                .get("search_by_raw_query", {})
                .get("search_timeline", {})
                .get("timeline", {})
                .get("instructions", [])
            )

            new_tweets = []
            for instruction in timeline:
                if "entries" in instruction:
                    for entry in instruction["entries"]:
                        if "content" in entry and "itemContent" in entry["content"]:
                            tweet_data = entry["content"]["itemContent"]
                            if tweet_data.get("__typename") == "TimelineTweet":
                                new_tweets.append(Tweet.from_api_response(tweet_data))

            # Add new tweets with deduplication
            all_tweets.extend(
                [
                    tweet
                    for tweet in new_tweets
                    if tweet and tweet.id not in {t.id for t in all_tweets}
                ]
            )

            # Stop if we've reached the desired count
            if count != -1 and len(all_tweets) >= count:
                all_tweets = all_tweets[:count]
                break

            # Get cursor for next page from bottom cursor entry
            for instruction in timeline:
                if "entry" in instruction and instruction["entry"][
                    "entryId"
                ].startswith("cursor-bottom-"):
                    cursor = instruction["entry"]["content"]["value"]
                    break
                elif "entries" in instruction:
                    for entry in instruction["entries"]:
                        if entry["entryId"].startswith("cursor-bottom-"):
                            cursor = entry["content"]["value"]
                            break

            # Stop if no cursor found or no new tweets
            if not cursor or not new_tweets:
                break

        return all_tweets

    def get_user_by_screen_name(
        self,
        screen_name: str,
        with_safety_mode_user_fields: bool = True,
        with_highlighted_label: bool = True,
    ) -> User:
        """Get detailed user information by screen name using GraphQL endpoint.

        Args:
            screen_name: Twitter screen name/username
            with_safety_mode_user_fields: Include safety mode user fields (default: True)
            with_highlighted_label: Include highlighted label information (default: True)

        Returns:
            User object containing detailed user information including profile data, stats, and verification status
        """
        variables = {
            "screen_name": screen_name,
            "withSafetyModeUserFields": with_safety_mode_user_fields,
            "withHighlightedLabel": with_highlighted_label,
        }

        response = self._make_request(
            "GET",
            "/graphql/UserByScreenName",
            params={"variables": variables},
        )

        if (
            response.get("data")
            and response["data"].get("user")
            and response["data"]["user"].get("result")
        ):
            return User.from_api_response(response["data"]["user"]["result"])

    def get_list_latest_tweets(
        self,
        list_id: Union[int, str],
        count: int = 20,
        include_promoted_content: bool = False,
    ) -> List[Tweet]:
        """Get latest tweets from a specific Twitter list using GraphQL endpoint.

        Args:
            list_id: ID of the Twitter list
            count: Number of tweets to return (default: 20, set to -1 for all available results)
            include_promoted_content: Include promoted content in results (default: False)

        Returns:
            List of Tweet objects from the specified list
        """
        all_tweets = []
        cursor = None

        while True:
            variables = {
                "listId": str(list_id),
                "count": count,
                "includePromotedContent": include_promoted_content,
            }
            if cursor:
                variables["cursor"] = cursor

            response = self._make_request(
                "GET",
                "/graphql/ListLatestTweetsTimeline",
                params={"variables": variables},
            )

            # Extract tweets from current page
            timeline = (
                response.get("data", {})
                .get("list", {})
                .get("tweets_timeline", {})
                .get("timeline", {})
                .get("instructions", [])
            )
            if not timeline:
                break

            entries = timeline[0].get("entries", [])
            new_tweets = []
            cursor = None

            for entry in entries:
                content = entry.get("content", {})

                # Handle regular tweets
                if content.get("__typename") == "TimelineTimelineItem":
                    tweet_data = content["itemContent"]
                    new_tweets.append(Tweet.from_api_response(tweet_data))

                # Extract cursor for next page
                elif (
                    content.get("__typename") == "TimelineTimelineCursor"
                    and content.get("cursorType") == "Bottom"
                ):
                    cursor = content.get("value")

                # Handle tweets in modules
                elif content.get("__typename") == "TimelineTimelineModule":
                    for item in content["items"]:
                        tweet_data = item["item"]["itemContent"]
                        new_tweets.append(Tweet.from_api_response(tweet_data))

            all_tweets.extend(new_tweets)

            # Stop if we've reached the desired count
            if count != -1 and len(all_tweets) >= count:
                all_tweets = all_tweets[:count]
                break

            # Stop if no cursor found or no new tweets
            if not cursor or not new_tweets:
                break

        return all_tweets

    def _extract_tweets_from_response(
        self, response: Dict, include_pins: bool
    ) -> List[Tweet]:
        """Extract tweets from API response.

        Args:
            response: Raw API response
            include_pins: Whether to include pinned tweets

        Returns:
            List of Tweet objects
        """
        tweets = []
        data = response.get("data", {}).get("user", {}).get("result", {})
        timeline = (
            data.get("timeline_v2", {}).get("timeline", {}).get("instructions", [])
        )

        for instruction in timeline:
            if "entries" in instruction:
                for entry in instruction["entries"]:
                    content = entry.get("content")
                    if content.get("__typename") == "TimelineTimelineItem":
                        tweet_data = content["itemContent"]
                        tweets.append(Tweet.from_api_response(tweet_data))
                    elif content.get("__typename") == "TimelineTimelineModule":
                        thread_data = content["items"]
                        for thread_item in thread_data:
                            tweet_data = thread_item.get("item").get("itemContent")
                            tweets.append(Tweet.from_api_response(tweet_data))
            elif (
                instruction.get("type") == "TimelinePinEntry"
                and "entry" in instruction
                and include_pins
            ):  # Pin tweet
                entry = instruction["entry"]
                if "content" in entry and "itemContent" in entry["content"]:
                    tweet_data = entry["content"]["itemContent"]
                    tweets.append(Tweet.from_api_response(tweet_data))

        return tweets

    def _get_bottom_cursor(self, response: Dict) -> Optional[str]:
        """Extract bottom cursor from API response.

        Args:
            response: Raw API response

        Returns:
            Cursor value if found, None otherwise
        """
        data = response.get("data", {}).get("user", {}).get("result", {})
        timeline = (
            data.get("timeline_v2", {}).get("timeline", {}).get("instructions", [])
        )

        for instruction in timeline:
            if "entries" in instruction:
                for entry in instruction["entries"]:
                    content = entry.get("content", {})
                    if (
                        content.get("__typename") == "TimelineTimelineCursor"
                        and content.get("cursorType") == "Bottom"
                    ):
                        return content.get("value")
        return None

    def has_more_tweets(self, response: Dict) -> bool:
        """Check if there are more tweets to fetch.

        Args:
            response: Raw API response

        Returns:
            True if there are more tweets, False otherwise
        """
        data = response.get("data", {}).get("user", {}).get("result", {})
        timeline = (
            data.get("timeline_v2", {}).get("timeline", {}).get("instructions", [])
        )

        for instruction in timeline:
            if "entries" in instruction:
                for entry in instruction["entries"]:
                    content = entry.get("content")
                    if content.get("__typename") == "TimelineTimelineItem":
                        return True
        return False

    def get_user_tweets(
        self,
        user_id: Union[int, str],
        count: int = 20,
        include_pins: bool = True,
        include_promoted_content: bool = False,
        with_quick_promote_eligibility_tweet_fields: bool = False,
        with_voice: bool = False,
        with_v2_timeline: bool = True,
    ) -> List[Tweet]:
        """Get tweets from a specific user using GraphQL endpoint.

        Args:
            user_id: Twitter user ID
            count: Number of tweets to return (default: 20, set to -1 for all tweets)
            include_promoted_content: Include promoted content in results (default: False)
            with_quick_promote_eligibility_tweet_fields: Include quick promote eligibility fields (default: False)
            with_voice: Include voice tweet information (default: False)
            with_v2_timeline: Include v2 timeline information (default: True)

        Returns:
            List of Tweet objects containing tweet content, media, and related information
        """
        all_tweets = []
        cursor = None
        batch_size = 20  # Twitter API limit

        while True:
            variables = {
                "userId": str(user_id),
                "count": batch_size,
                "cursor": cursor,
                "includePromotedContent": include_promoted_content,
                "withQuickPromoteEligibilityTweetFields": with_quick_promote_eligibility_tweet_fields,
                "withVoice": with_voice,
                "withV2Timeline": with_v2_timeline,
            }

            response = self._make_request(
                "GET",
                "/graphql/UserTweets",
                params={"variables": variables},
            )

            # Extract tweets from response
            new_tweets = self._extract_tweets_from_response(
                response, include_pins=include_pins
            )
            all_tweets.extend(
                [
                    tweet
                    for tweet in new_tweets
                    if tweet and tweet.id not in {t.id for t in all_tweets}
                ]
            )

            # Stop if we've reached the desired count
            if count != -1 and len(all_tweets) >= count:
                all_tweets = all_tweets[:count]
                break

            # Check if there are more tweets to fetch
            if not self.has_more_tweets(response):
                break

            # Get cursor for next page
            cursor = self._get_bottom_cursor(response)
            if not cursor:
                break

        return all_tweets

    def get_following(self, user_id: Union[int, str]) -> List[User]:
        """Get a list of users that the specified user is following.

        Args:
            user_id: The user ID to get following for

        Returns:
            List of User objects
        """

        variables = {
            "userId": str(user_id),
            "includePromotedContent": False,
        }

        response = self._make_request(
            "GET",
            "/graphql/Following",
            params={"variables": variables},
        )

        # Extract users from the nested timeline structure
        if not isinstance(response, dict):
            return []
        data = response.get("data", {}).get("user", {}).get("result", {})
        timeline = data.get("timeline", {}).get("timeline", {})
        instructions = timeline.get("instructions", [])

        users = []
        for instruction in instructions:
            # Skip TimelineClearCache type instructions
            if instruction.get("type") == "TimelineClearCache":
                continue

            # Handle entries if present
            entries = instruction.get("entries", [])
            if entries:
                for entry in entries:
                    content = entry.get("content", {})
                    if (
                        content.get("itemContent", {})
                        .get("user_results", {})
                        .get("result")
                    ):
                        user_data = content["itemContent"]["user_results"]["result"]
                        users.append(User.from_api_response(user_data))

        return users

    def get_followers(
        self,
        user_id: Union[int, str],
        count: int = 20,
        include_promoted_content: bool = False,
    ) -> List[User]:
        """Get a list of followers for a specific user using GraphQL endpoint.

        Args:
            user_id: Twitter user ID
            count: Number of followers to return (default: 20, set to -1 for all followers)
            include_promoted_content: Include promoted content in results (default: False)

        Returns:
            List of User objects containing detailed user information
        """
        variables = {
            "userId": str(user_id),
            "count": min(count, 20) if count > 0 else 20,
            "includePromotedContent": include_promoted_content,
        }

        all_followers = []
        cursor = None

        while True:
            if cursor:
                variables["cursor"] = cursor

            response = self._make_request(
                "GET",
                "/graphql/Followers",
                params={"variables": variables},
            )

            try:
                entries = response["data"]["user"]["result"]["timeline"]["timeline"][
                    "instructions"
                ][-1]["entries"]
            except (KeyError, IndexError):
                break

            # Extract users from the response
            for entry in entries:
                if entry["content"].get("__typename") == "TimelineTimelineItem":
                    try:
                        user_data = entry["content"]["itemContent"]["user_results"][
                            "result"
                        ]
                        if user_data["__typename"] == "User":
                            all_followers.append(User.from_api_response(user_data))
                    except (KeyError, TypeError):
                        continue

            # Check if we need to continue fetching
            if count != -1 and len(all_followers) >= count:
                all_followers = all_followers[:count]
                break

            # Look for the bottom cursor
            cursor = None
            for entry in entries:
                if (
                    entry["content"].get("__typename") == "TimelineTimelineCursor"
                    and entry["content"].get("cursorType") == "Bottom"
                ):
                    cursor = entry["content"].get("value")
                    break

            if not cursor:
                break

            # If we got less than requested in this batch, no need to continue
            if count > 0 and len(entries) < variables["count"]:
                break

        return all_followers

    def get_followers_you_know(
        self,
        user_id: Union[int, str],
        count: int = 20,
        include_promoted_content: bool = False,
    ) -> List[User]:
        """Get a list of followers that you know for a specific user using GraphQL endpoint.

        Args:
            user_id: Twitter user ID
            count: Number of followers to return (default: 20, set to -1 for all followers)
            include_promoted_content: Include promoted content in results (default: False)

        Returns:
            List of User objects containing detailed user information
        """
        variables = {
            "userId": str(user_id),
            "count": min(count, 20) if count > 0 else 20,
            "includePromotedContent": include_promoted_content,
        }

        all_followers = []
        cursor = None

        while True:
            if cursor:
                variables["cursor"] = cursor

            response = self._make_request(
                "GET",
                "/graphql/FollowersYouKnow",
                params={"variables": variables},
            )

            try:
                entries = response["data"]["user"]["result"]["timeline"]["timeline"][
                    "instructions"
                ][-1]["entries"]
            except (KeyError, IndexError):
                break

            # Extract users from the response
            for entry in entries:
                if entry["content"].get("__typename") == "TimelineTimelineItem":
                    try:
                        user_data = entry["content"]["itemContent"]["user_results"][
                            "result"
                        ]
                        if user_data["__typename"] == "User":
                            all_followers.append(User.from_api_response(user_data))
                    except (KeyError, TypeError):
                        continue

            # Check if we need to continue fetching
            if count != -1 and len(all_followers) >= count:
                all_followers = all_followers[:count]
                break

            # Look for the bottom cursor
            cursor = None
            for entry in entries:
                if (
                    entry["content"].get("__typename") == "TimelineTimelineCursor"
                    and entry["content"].get("cursorType") == "Bottom"
                ):
                    cursor = entry["content"].get("value")
                    break

            if not cursor:
                break

            # If we got less than requested in this batch, no need to continue
            if count > 0 and len(entries) < variables["count"]:
                break

        return all_followers

    def favorite_tweet(self, tweet_id: Union[int, str]) -> bool:

        variables = {
            "tweet_id": str(tweet_id),
        }

        response = self._make_request(
            "POST",
            "/graphql/FavoriteTweet",
            json={"variables": variables},
        )
        if response == {"data": {"favorite_tweet": "Done"}}:
            print(f"Tweet: {tweet_id} favorited")
            return True

        if len(response) == 0:
            print(f"Tweet: {tweet_id} not favorited")
            return False

        if response["errors"][0]["code"] == 139:
            print(f"Tweet: {tweet_id} already favorited")
            return True

        if response["errors"][0]["code"] == 144:
            print(f"Tweet: {tweet_id} not found")
            return False

        return False

    def create_tweet(self, text: str, reply_to_tweet_id: Union[int, str] = None) -> str:
        """Create a new tweet or reply to an existing tweet.

        Args:
            text: The text content of the tweet
            reply_to_tweet_id: Optional tweet ID to reply to

        Returns:
            str: The ID of the created tweet
        """
        variables = {
            "tweet_text": text,
            "dark_request": False,
            "media": {"media_entities": [], "possibly_sensitive": False},
            "semantic_annotation_ids": [],
        }

        # Add reply information if replying to a tweet
        if reply_to_tweet_id:
            variables["reply"] = {
                "in_reply_to_tweet_id": str(reply_to_tweet_id),
                "exclude_reply_user_ids": [],
            }

        response = self._make_request(
            "POST",
            "/graphql/CreateTweet",
            json={"variables": variables},
        )

        # Extract the tweet ID from the response
        try:
            tweet_id = response["data"]["create_tweet"]["tweet_results"]["result"][
                "rest_id"
            ]
            print(f"Tweet created successfully with ID: {tweet_id}")
            return tweet_id
        except (KeyError, TypeError):
            print("Failed to create tweet")
            return None

    def create_note_tweet(
        self,
        text: str,
        use_richtext: bool = False,
        reply_to_tweet_id: Union[int, str] = None,
    ) -> str:
        """Create a new note tweet. (Long text tweet, only available in Premium+)

        Args:
            text: The text content of the tweet (supports markdown if use_richtext=True)
            use_richtext: Whether to parse markdown formatting for rich text
            reply_to_tweet_id: Optional tweet ID to reply to

        Returns:
            str: The ID of the created tweet

        Raises:
            PremiumRequiredError: If the user doesn't have Premium+ plan
        """
        richtext_options = {}

        variables = {
            "tweet_text": text,
            "dark_request": False,
            "media": {"media_entities": [], "possibly_sensitive": False},
            "semantic_annotation_ids": [],
            "includePromotedContent": False,
        }

        if use_richtext:
            text, richtext_tags = parse_markdown_to_richtext(text)
            if richtext_tags:
                richtext_options["richtext_tags"] = richtext_tags
                variables["richtext_options"] = richtext_options

        # Add reply information if replying to a tweet
        if reply_to_tweet_id:
            variables["reply"] = {
                "in_reply_to_tweet_id": str(reply_to_tweet_id),
                "exclude_reply_user_ids": [],
            }

        response = self._make_request(
            "POST",
            "/graphql/CreateNoteTweet",
            json={"variables": variables},
        )

        # Extract the tweet ID from the response
        try:
            tweet_id = response["data"]["notetweet_create"]["tweet_results"]["result"][
                "rest_id"
            ]
            print(f"Note tweet created successfully with ID: {tweet_id}")
            return tweet_id
        except (KeyError, TypeError):
            print("Failed to create note tweet")
            return None

    def tweet_result_by_rest_id(self, tweet_id: Union[int, str]):
        variables = {
            "tweetId": str(tweet_id),
            "withHighlightedLabel": True,
            "withTweetQuoteCount": True,
            "includePromotedContent": True,
            "withBirdwatchPivots": True,
            "withVoice": True,
            "withReactions": True,
        }

        response = self._make_request(
            "GET",
            "/graphql/TweetResultByRestId",
            params={"variables": variables},
        )

        # {'data': {'tweetResult': {}}}
        # response maybe []

        return Tweet.from_api_response(response["data"])
