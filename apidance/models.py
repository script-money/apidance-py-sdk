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
    url: Optional[str] = None

    @classmethod
    def from_api_response(cls, data: Dict) -> "User":
        legacy = data.get("legacy", {})
        description = legacy.get("description")

        entities = legacy.get("entities", {})
        if description and entities.get("description", {}).get("urls"):
            for url_data in entities["description"]["urls"]:
                description = description.replace(
                    url_data["url"], url_data["expanded_url"]
                )

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
    id: str
    name: str
    screen_name: str


@dataclass
class Tweet:
    id: str
    text: str
    created_at: int  # Unix timestamp
    userid: str
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
            id=legacy.get("id_str", ""),
            text=legacy.get("full_text", ""),
            created_at=int(
                datetime.strptime(
                    legacy.get("created_at", ""), "%a %b %d %H:%M:%S %z %Y"
                ).timestamp()
            ),
            userid=core.get("user_results", {}).get("result", {}).get("rest_id", ""),
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
