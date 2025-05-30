from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel


class BaseApiModel(BaseModel):
    """Base model for all Apidance models with dict-like access and serialization support."""

    def __getitem__(self, item):
        return getattr(self, item)

    def model_dump(self, **kwargs):
        """Override model_dump to handle datetime serialization."""
        kwargs.setdefault("mode", "json")
        return super().model_dump(**kwargs)


class User(BaseApiModel):
    id: str
    name: str
    username: str
    followers_count: int
    following_count: int
    description: Optional[str] = None
    url: Optional[str] = None
    is_verified: bool = False
    is_business: bool = False

    @classmethod
    def from_api_response(cls, data: Dict) -> "User":
        legacy = data.get("legacy", {})
        description = legacy.get("description")

        entities = legacy.get("entities", {})
        if description and entities.get("description", {}).get("urls"):
            for url_data in entities["description"]["urls"]:
                description = description.replace(
                    url_data["url"], url_data.get("expanded_url", "")
                )

        is_verified = data.get("is_blue_verified", False)
        is_business = True if legacy.get("verified_type") == "Business" else False

        profile_url = ""
        if entities.get("url", {}).get("urls"):
            profile_url = (
                entities.get("url", {}).get("urls", [{}])[0].get("expanded_url", "")
            )

        return cls(
            id=data.get("rest_id", ""),
            name=legacy.get("name", ""),
            username=legacy.get("screen_name", ""),
            followers_count=legacy.get("followers_count", 0),
            following_count=legacy.get("friends_count", 0),
            description=description,
            url=profile_url,
            is_verified=is_verified,
            is_business=is_business,
        )


class Media(BaseApiModel):
    type: str  # photo, video, etc.
    url: str
    expanded_url: Optional[str] = None
    preview_url: Optional[str] = None


class URL(BaseApiModel):
    url: str
    expanded_url: Optional[str] = None


class UserMention(BaseApiModel):
    id: str
    name: str
    screen_name: str


class Tweet(BaseApiModel):
    id: str
    text: str
    created_at: int  # Unix timestamp
    userid: str
    favorite_count: int
    retweet_count: int
    reply_count: int
    quote_count: int
    bookmark_count: int
    media: Optional[List[Media]] = None
    urls: Optional[List[URL]] = None
    user_mentions: Optional[List[UserMention]] = None
    is_retweet: bool = False
    retweet_status: Optional["Tweet"] = None

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "Tweet":
        """Create a Tweet instance from API response data.

        Args:
            data: A dictionary containing tweet data from the API response.

        Returns:
            A Tweet object constructed from the provided data.
        """

        # Get tweet result from either "tweet_results" or "tweetResult"
        if data.get("tweet_results") == {} or data.get("tweetResult") == {}:
            return

        tweet_result = data.get("tweet_results", {}).get("result") or data.get(
            "tweetResult", {}
        ).get("result", {})

        # Handle visibility results and extract legacy data
        legacy = (
            tweet_result["tweet"]["legacy"]
            if tweet_result.get("__typename") == "TweetWithVisibilityResults"
            else tweet_result.get("legacy", tweet_result)
        )

        note_tweet = tweet_result.get("note_tweet", {})

        # Get user ID from various possible locations
        userid = (
            tweet_result.get("core", {})
            .get("user_results", {})
            .get("result", {})
            .get("rest_id")
            or legacy.get("user_id_str")
            or tweet_result.get("user_id_str", "")
        )

        # Get text content from various possible locations
        text = (
            (
                legacy.get("full_text")
                or tweet_result.get("full_text")
                or legacy.get("text", "")
            )
            if note_tweet == {}
            else (
                note_tweet.get("note_tweet_results", {})
                .get("result", {})
                .get("text", "")
            )
        )

        # Parse URL and user mentions
        urls = []
        if "entities" in legacy and "urls" in legacy["entities"]:
            for url in legacy["entities"]["urls"]:
                urls.append(
                    URL(
                        url=url["url"],
                        expanded_url=url.get("expanded_url"),
                    )
                )

        user_mentions = []
        if "entities" in legacy and "user_mentions" in legacy["entities"]:
            for mention in legacy["entities"]["user_mentions"]:
                user_mentions.append(
                    UserMention(
                        id=mention["id_str"],
                        name=mention["name"],
                        screen_name=mention["screen_name"],
                    )
                )

        # Parse media data
        media_list = []
        if "extended_entities" in legacy and "media" in legacy["extended_entities"]:
            for media_item in legacy["extended_entities"]["media"]:
                media_type = media_item.get("type", "photo")
                media = Media(
                    type=media_type,
                    url=media_item.get("url", ""),
                    expanded_url=media_item.get("expanded_url", ""),
                    preview_url=media_item.get("media_url_https", ""),
                )
                media_list.append(media)

        # Parse retweet data
        is_retweet = "retweeted_status_result" in legacy
        retweet_status = None
        if is_retweet:
            retweet_data = legacy.get("retweeted_status_result", {})
            retweet_status = cls.from_api_response(
                {"tweet_results": {"result": retweet_data.get("result", {})}}
            )

        return cls(
            id=legacy.get("id_str") or tweet_result.get("id_str", ""),
            text=text,
            created_at=int(
                datetime.strptime(
                    legacy.get("created_at") or tweet_result.get("created_at", ""),
                    "%a %b %d %H:%M:%S %z %Y",
                ).timestamp()
            ),
            userid=userid,
            favorite_count=legacy.get("favorite_count", 0),
            retweet_count=legacy.get("retweet_count", 0),
            reply_count=legacy.get("reply_count", 0),
            quote_count=legacy.get("quote_count", 0),
            bookmark_count=legacy.get("bookmark_count", 0),
            media=media_list if media_list else None,
            urls=urls if urls else None,
            user_mentions=user_mentions if user_mentions else None,
            is_retweet=is_retweet,
            retweet_status=retweet_status,
        )
