from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class User:
    id: str
    name: str
    username: str
    followers_count: int
    following_count: int
    description: Optional[str] = None

    @classmethod
    def from_api_response(cls, data: Dict) -> "User":
        return cls(
            id=data.get("id", ""),
            name=data.get("legacy", {}).get("name", ""),
            username=data.get("legacy", {}).get("screen_name", ""),
            followers_count=data.get("legacy", {}).get("followers_count", 0),
            following_count=data.get("legacy", {}).get("friends_count", 0),
            description=data.get("legacy", {}).get("description"),
        )


@dataclass
class Media:
    type: str  # photo, video, etc.
    url: str
    expanded_url: str
    preview_url: Optional[str] = None


@dataclass
class URL:
    display_url: str
    expanded_url: str
    url: str


@dataclass
class UserMention:
    id_str: str
    name: str
    screen_name: str


@dataclass
class Tweet:
    id: str
    text: str
    created_at: int  # Unix timestamp
    user: User
    favorite_count: int
    retweet_count: int
    reply_count: int
    quote_count: int
    media: Optional[List[Media]] = None
    urls: Optional[List[URL]] = None
    user_mentions: Optional[List[UserMention]] = None
    is_retweet: bool = False
    retweet_status: Optional["Tweet"] = None

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "Tweet":
        """Create a Tweet instance from API response data."""
        result = data.get("tweet_results", {}).get("result", {})
        legacy = result.get("legacy", {})
        if legacy == {}:
            legacy = result.get("tweet", {}).get("legacy", {})
        core = result.get("core", {}) or {}
        user_data = core.get("user_results", {}).get("result", {}).get("legacy", {})

        # Parse user data
        user = User(
            id=core.get("user_results", {}).get("result", {}).get("rest_id", ""),
            name=user_data.get("name", ""),
            username=user_data.get("screen_name", ""),
            followers_count=user_data.get("followers_count", 0),
            following_count=user_data.get("friends_count", 0),
            description=user_data.get("description"),
        )

        # Parse URL and user mentions
        urls = []
        if "entities" in legacy and "urls" in legacy["entities"]:
            for url in legacy["entities"]["urls"]:
                urls.append(
                    URL(
                        display_url=url["display_url"],
                        expanded_url=url["expanded_url"],
                        url=url["url"],
                    )
                )

        user_memtions = []
        if "entities" in legacy and "user_mentions" in legacy["entities"]:
            for mention in legacy["entities"]["user_mentions"]:
                user_memtions.append(
                    UserMention(
                        id_str=mention["id_str"],
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
            id=legacy.get("id_str", ""),
            text=legacy.get("full_text", ""),
            created_at=int(
                datetime.strptime(
                    legacy.get("created_at", ""), "%a %b %d %H:%M:%S %z %Y"
                ).timestamp()
            ),
            user=user,
            favorite_count=legacy.get("favorite_count", 0),
            retweet_count=legacy.get("retweet_count", 0),
            reply_count=legacy.get("reply_count", 0),
            quote_count=legacy.get("quote_count", 0),
            media=media_list if media_list else None,
            urls=urls if urls else None,
            user_mentions=user_memtions if user_memtions else None,
            is_retweet=is_retweet,
            retweet_status=retweet_status,
        )
