import os
import json
import time
from typing import Optional, Dict, Any, List
import httpx
from dotenv import load_dotenv
from apidance.models import Tweet, User
from .exceptions import AuthenticationError

load_dotenv()


class TwitterClient:
    """Client for interacting with Twitter API via Apidance."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Twitter client.

        Args:
            api_key: Optional API key. If not provided, will be read from APIDANCE_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("APIDANCE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "API key must be provided either through constructor or APIDANCE_API_KEY environment variable"
            )

        # Check balance
        balance = self.check_balance()
        if int(balance) < 100:
            print(
                f"Warning: Your API balance is low ({balance}). Please recharge your account."
            )
            response = input("Do you want to continue? [y/N]: ")
            if response.lower() != "y":
                raise SystemExit("Operation cancelled by user.")

        self.base_url = "https://api.apidance.pro"
        self.client = httpx.Client()
        self.headers = {
            "apikey": self.api_key,
            "Content-Type": "application/json",
        }

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make a request to the API.

        Args:
            method: HTTP method to use
            endpoint: API endpoint
            **kwargs: Additional arguments to pass to the request

        Returns:
            API response data

        Raises:
            AuthenticationError: If authentication fails for POST requests
            TimeoutError: If the request times out
        """
        url = f"{self.base_url}{endpoint}"

        # If variables are present in params, JSON encode them
        if "params" in kwargs and "variables" in kwargs["params"]:
            kwargs["params"]["variables"] = json.dumps(kwargs["params"]["variables"])

        # For POST requests, check for auth token
        headers = self.headers.copy()
        if method.upper() == "POST":
            token = os.getenv("X_AUTH_TOKEN")
            if token:
                headers["AuthToken"] = token

        max_retries = 10
        for i in range(1, max_retries + 1):
            try:
                response = self.client.request(
                    method, url, headers=headers, timeout=10, **kwargs
                )
            except httpx.ConnectTimeout:
                raise TimeoutError("The handshake operation timed out") from None

            if (
                response.status_code != 200
                or response.text == "local_rate_limited"
                or response.text == "null"
                or "errors" in response.json()
            ):
                # Check for authentication error and rate limits
                try:
                    error_data = response.json()
                    if error_data.get("errors"):
                        error = error_data["errors"][0]
                        if error.get("code") == 32:
                            raise AuthenticationError(
                                "Could not authenticate you. Please check your X_AUTH_TOKEN."
                            )
                        elif error.get("code") == 88:
                            # Rate limit error, will retry
                            if i == max_retries:  # If this was the last retry
                                return None
                            time.sleep(1)
                        else:
                            return error_data
                except json.JSONDecodeError:
                    pass

                if i == max_retries:  # If this was the last retry
                    return None
                time.sleep(1)
            else:
                return response.json()

    def check_balance(self) -> int:
        """Check the remaining balance for the API key.

        Returns:
            int: Remaining balance
        """
        response = httpx.get(f"https://api.apidance.pro/key/{self.api_key}")
        return response.text

    def search_timeline(
        self,
        query: str,
        product: str = "Latest",
        count: int = 40,
        cursor: str = "",
        include_promoted_content: bool = False,
    ) -> List[Tweet]:
        """Search Twitter timeline.

        Args:
            query: Search query string
            product: Type of search results. One of: Top, Latest, People, Photos, Videos
            count: Number of results to return (default: 40)
            cursor: Pagination cursor (default: "")
            include_promoted_content: Whether to include promoted content (default: False)

        Returns:
            List of Tweet objects from search results
        """
        variables = {
            "rawQuery": query,
            "count": count,
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

        tweets = []
        timeline = (
            response.get("data", {})
            .get("search_by_raw_query", {})
            .get("search_timeline", {})
            .get("timeline", {})
            .get("instructions", [])
        )
        for instruction in timeline:
            if "entries" in instruction:
                for entry in instruction["entries"]:
                    if "content" in entry and "itemContent" in entry["content"]:
                        tweet_data = entry["content"]["itemContent"]
                        if tweet_data.get("__typename") == "TimelineTweet":
                            tweets.append(Tweet.from_api_response(tweet_data))

        return tweets

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
        list_id: str,
        count: int = 20,
        include_promoted_content: bool = False,
    ) -> List[Tweet]:
        """Get latest tweets from a specific Twitter list using GraphQL endpoint.

        Args:
            list_id: ID of the Twitter list
            count: Number of tweets to return (default: 20)
            include_promoted_content: Include promoted content in results (default: False)

        Returns:
            List of Tweet objects from the specified list
        """
        variables = {
            "listId": list_id,
            "count": count,
            "includePromotedContent": include_promoted_content,
        }

        response = self._make_request(
            "GET",
            "/graphql/ListLatestTweetsTimeline",
            params={"variables": variables},
        )

        tweets = []
        timeline = (
            response.get("data", {})
            .get("list", {})
            .get("tweets_timeline", {})
            .get("timeline", {})
            .get("instructions", [])
        )
        for instruction in timeline:
            if "entries" in instruction:
                for entry in instruction["entries"]:
                    if "content" in entry and "itemContent" in entry["content"]:
                        tweet_data = entry["content"]["itemContent"]
                        if tweet_data.get("__typename") == "TimelineTweet":
                            tweets.append(Tweet.from_api_response(tweet_data))

        return tweets

    def get_user_tweets(
        self,
        user_id: str,
        count: int = 20,
        include_promoted_content: bool = False,
        with_quick_promote_eligibility_tweet_fields: bool = True,
        with_voice: bool = True,
        with_v2_timeline: bool = True,
    ) -> List[Tweet]:
        """Get tweets from a specific user using GraphQL endpoint.

        Args:
            user_id: Twitter user ID
            count: Number of tweets to return (default: 20)
            include_promoted_content: Include promoted content in results (default: False)
            with_quick_promote_eligibility_tweet_fields: Include quick promote eligibility fields (default: True)
            with_voice: Include voice tweet information (default: True)
            with_v2_timeline: Include v2 timeline information (default: True)

        Returns:
            List of Tweet objects containing tweet content, media, and related information
        """
        variables = {
            "userId": user_id,
            "count": count,
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
                instruction.get("type") == "TimelinePinEntry" and "entry" in instruction
            ):  # Pin tweet
                entry = instruction["entry"]
                if "content" in entry and "itemContent" in entry["content"]:
                    tweet_data = entry["content"]["itemContent"]
                    tweets.append(Tweet.from_api_response(tweet_data))

        return tweets

    def get_following(self, user_id: str) -> List[User]:
        """Get a list of users that the specified user is following.

        Args:
            user_id: The user ID to get following for

        Returns:
            List of User objects
        """

        variables = {
            "userId": user_id,
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

    def favorite_tweet(self, tweet_id: str) -> bool:

        variables = {
            "tweet_id": tweet_id,
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

    def create_tweet(self, text: str, reply_to_tweet_id: str = None) -> str:
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
                "in_reply_to_tweet_id": reply_to_tweet_id,
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

    def tweet_result_by_rest_id(self, tweet_id: str):
        variables = {
            "tweetId": tweet_id,
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

        # response maybe []

        return Tweet.from_api_response(response["data"])
