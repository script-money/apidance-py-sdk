from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class User:
    id: str
    name: str
    username: str
    profile_image_url: str
    followers_count: int
    following_count: int
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    profile_banner_url: Optional[str] = None
    media_count: Optional[int] = None
    listed_count: Optional[int] = None
    favourites_count: Optional[int] = None
    statuses_count: Optional[int] = None
    location: Optional[str] = None
    url: Optional[str] = None
    is_blue_verified: Optional[bool] = None
    is_profile_translatable: Optional[bool] = None
    has_custom_timelines: Optional[bool] = None
    possibly_sensitive: Optional[bool] = None
    verified: Optional[bool] = None
    profile_image_shape: Optional[str] = None

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "User":
        """Create a User instance from GraphQL API response data."""

        # {'__typename': 'User', 'affiliates_highlighted_label': {}, 'business_account': {}, 'creator_subscriptions_count': 0, 'has_graduated_access': True, 'highlights_info': {'can_highlight_tweets': True, 'highlighted_tweets': '0'}, 'id': 'VXNlcjoxNzYwNDg5MTczMTY4MDQ2MDgw', 'is_blue_verified': True, 'is_profile_translatable': False, 'legacy': {'can_dm': True, 'can_media_tag': True, 'created_at': 'Thu Feb 22 02:18:49 +0000 2024', 'default_profile': True, 'default_profile_image': False, 'description': 'AICell integrates AI agent and web3,  the one and only AI Agent on #BNBChain.', 'entities': {...}, 'fast_followers_count': 0, 'favourites_count': 1, 'followers_count': 1800, 'friends_count': 8, 'has_custom_timelines': False, 'is_translator': False, 'listed_count': 8, 'location': '', 'media_count': 25, 'name': 'AICell', 'normal_followers_count': 1800, 'pinned_tweet_ids_str': [...], ...}, 'legacy_extended_profile': {}, 'profile_image_shape': 'Circle', 'rest_id': '1760489173168046080', 'smart_blocked_by': False, 'smart_blocking': False, 'verification_info': {'reason': {...}}}
        return cls(
            id=data.get("id", ""),
            name=data.get("legacy", {}).get("name", ""),
            username=data.get("legacy", {}).get("screen_name", ""),
            profile_image_url=data.get("legacy", {}).get("profile_image_url_https", ""),
            followers_count=data.get("legacy", {}).get("followers_count", 0),
            following_count=data.get("legacy", {}).get("friends_count", 0),
            description=data.get("legacy", {}).get("description"),
            created_at=data.get("legacy", {}).get("created_at"),
            profile_banner_url=data.get("legacy", {}).get("profile_banner_url"),
            media_count=data.get("legacy", {}).get("media_count"),
            listed_count=data.get("legacy", {}).get("listed_count"),
            favourites_count=data.get("legacy", {}).get("favourites_count"),
            statuses_count=data.get("legacy", {}).get("statuses_count"),
            location=data.get("legacy", {}).get("location"),
            url=data.get("legacy", {}).get("url"),
            is_blue_verified=data.get("is_blue_verified"),
            is_profile_translatable=data.get("is_profile_translatable"),
            has_custom_timelines=data.get("legacy", {}).get("has_custom_timelines"),
            possibly_sensitive=data.get("legacy", {}).get("possibly_sensitive"),
            verified=data.get("legacy", {}).get("verified"),
            profile_image_shape=data.get("profile_image_shape"),
        )


@dataclass
class Media:
    type: str  # photo, video, etc.
    url: str
    preview_url: Optional[str] = None
    duration_ms: Optional[int] = None  # for videos


@dataclass
class Tweet:
    id: str
    text: str
    created_at: datetime
    user: User
    favorite_count: int
    retweet_count: int
    reply_count: int
    quote_count: int
    media: Optional[List[Media]] = None
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
            profile_image_url=user_data.get("profile_image_url_https", ""),
            followers_count=user_data.get("followers_count", 0),
            following_count=user_data.get("friends_count", 0),
            description=user_data.get("description"),
            created_at=(
                datetime.strptime(
                    user_data.get("created_at", ""), "%a %b %d %H:%M:%S %z %Y"
                )
                if user_data.get("created_at")
                else None
            ),
        )

        # Parse media data
        media_list = []
        if "extended_entities" in legacy and "media" in legacy["extended_entities"]:
            for media_item in legacy["extended_entities"]["media"]:
                media_type = media_item.get("type", "photo")
                media = Media(
                    type=media_type,
                    url=media_item.get("media_url_https", "")
                    or media_item.get("expanded_url", ""),
                    preview_url=(
                        media_item.get("media_url_https")
                        if media_type == "video"
                        else None
                    ),
                    duration_ms=(
                        media_item.get("video_info", {}).get("duration_millis")
                        if media_type == "video"
                        else None
                    ),
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
            created_at=datetime.strptime(
                legacy.get("created_at", ""), "%a %b %d %H:%M:%S %z %Y"
            ),
            user=user,
            favorite_count=legacy.get("favorite_count", 0),
            retweet_count=legacy.get("retweet_count", 0),
            reply_count=legacy.get("reply_count", 0),
            quote_count=legacy.get("quote_count", 0),
            media=media_list if media_list else None,
            is_retweet=is_retweet,
            retweet_status=retweet_status,
        )
