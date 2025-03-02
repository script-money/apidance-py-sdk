from typing import Optional, Dict, Any, Union
import os
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from apidance.client import TwitterClient

# Load environment variables
load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("twitter")

# Client instance
twitter_client: Optional[TwitterClient] = None


def initialize_client() -> None:
    """
    Initialize the Twitter client with API key from environment variables.
    This is called once at server startup.
    """
    global twitter_client

    # Get API key from environment
    api_key = os.getenv("APIDANCE_API_KEY")
    if not api_key:
        print("Warning: APIDANCE_API_KEY environment variable not set")
        return

    # Initialize the client
    try:
        twitter_client = TwitterClient(api_key=api_key)
        print("Twitter client initialized successfully")
    except Exception as e:
        print(f"Error initializing Twitter client: {str(e)}")


@mcp.tool()
async def create_tweet(
    text: str, reply_to_tweet_id: Optional[Union[int, str]] = None
) -> Dict[str, Any]:
    """
    Create a new tweet or reply to an existing tweet.

    Args:
        text: The text content of the tweet
        reply_to_tweet_id: Optional tweet ID to reply to

    Returns:
        Dict containing the tweet ID and status
    """
    if twitter_client is None:
        return {
            "success": False,
            "message": "Twitter client not initialized. Check APIDANCE_API_KEY environment variable.",
        }

    try:
        # Create the tweet
        tweet_id = twitter_client.create_tweet(
            text=text, reply_to_tweet_id=reply_to_tweet_id
        )

        if tweet_id:
            return {
                "success": True,
                "tweet_id": tweet_id,
                "message": "Tweet created successfully",
            }
        else:
            return {"success": False, "message": "Failed to create tweet"}
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "An unexpected error occurred",
        }


@mcp.tool()
async def get_tweet_by_id(tweet_id: Union[int, str]) -> Dict[str, Any]:
    """
    Get details about a specific tweet by its ID.

    Args:
        tweet_id: The ID of the tweet to retrieve

    Returns:
        Dict containing the tweet details
    """
    if twitter_client is None:
        return {
            "success": False,
            "message": "Twitter client not initialized. Check APIDANCE_API_KEY environment variable.",
        }

    try:
        tweet = twitter_client.tweet_result_by_rest_id(tweet_id)

        if tweet:
            return {"success": True, "tweet": tweet.model_dump()}
        else:
            return {"success": False, "message": "Tweet not found"}
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to retrieve tweet",
        }


@mcp.tool()
async def search_tweets(
    query: str, product: str = "Latest", count: int = 20
) -> Dict[str, Any]:
    """
    Search tweets to get information about specific topics or keywords.

    Args:
        query: Search query string, supports Twitter advanced search syntax
        product: Type of search results. One of: Top, Latest, People, Photos, Videos
        count: Number of results to return

    Returns:
        Dict containing the search results
    """
    if twitter_client is None:
        return {
            "success": False,
            "message": "Twitter client not initialized. Check APIDANCE_API_KEY environment variable.",
        }

    try:
        # Search tweets
        search_results = twitter_client.search_timeline(
            query=query, product=product, count=count
        )

        if search_results:
            # Convert Tweet objects to dictionaries
            tweets_data = [tweet.model_dump() for tweet in search_results]
            return {
                "success": True,
                "tweets": tweets_data,
                "count": len(tweets_data),
                "message": f"Found {len(tweets_data)} tweets matching query: {query}",
            }
        else:
            return {
                "success": True,
                "tweets": [],
                "count": 0,
                "message": f"No tweets found matching query: {query}",
            }
    except Exception as e:
        return {"success": False, "error": str(e), "message": "Failed to search tweets"}


@mcp.tool()
async def get_user_info(screen_name: str) -> Dict[str, Any]:
    """
    Get detailed user information by screen name.

    Args:
        screen_name: Twitter username (without @ symbol)

    Returns:
        Dict containing user information
    """
    if twitter_client is None:
        return {
            "success": False,
            "message": "Twitter client not initialized. Check APIDANCE_API_KEY environment variable.",
        }

    try:
        # Get user information
        user_info = twitter_client.get_user_by_screen_name(screen_name=screen_name)

        if user_info:
            return {
                "success": True,
                "user": user_info.model_dump(),
                "message": f"Successfully retrieved user information for @{screen_name}",
            }
        else:
            return {"success": False, "message": f"User @{screen_name} not found"}
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to retrieve user information for @{screen_name}",
        }


@mcp.tool()
async def get_user_tweets(
    user_id: Union[str, int] = None, screen_name: str = None, count: int = 20
) -> Dict[str, Any]:
    """
    Get tweets from a specific user.

    Args:
        user_id: User ID (either user_id or screen_name must be provided)
        screen_name: Username (either user_id or screen_name must be provided)
        count: Number of tweets to return

    Returns:
        Dict containing user tweets
    """
    if twitter_client is None:
        return {
            "success": False,
            "message": "Twitter client not initialized. Check APIDANCE_API_KEY environment variable.",
        }

    try:
        # If screen_name is provided but not user_id, get the user_id first
        if screen_name and not user_id:
            user_info = twitter_client.get_user_by_screen_name(screen_name=screen_name)
            if not user_info:
                return {"success": False, "message": f"User @{screen_name} not found"}
            user_id = user_info.id

        # Validate we have a user_id
        if not user_id:
            return {
                "success": False,
                "message": "Either user_id or screen_name must be provided",
            }

        # Get user tweets
        tweets = twitter_client.get_user_tweets(user_id=user_id, count=count)

        if tweets:
            # Convert Tweet objects to dictionaries
            tweets_data = [tweet.model_dump() for tweet in tweets]
            return {
                "success": True,
                "tweets": tweets_data,
                "count": len(tweets_data),
                "user_id": user_id,
                "message": f"Found {len(tweets_data)} tweets for user ID: {user_id}",
            }
        else:
            return {
                "success": True,
                "tweets": [],
                "count": 0,
                "user_id": user_id,
                "message": f"No tweets found for user ID: {user_id}",
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to retrieve user tweets",
        }


@mcp.tool()
async def create_note_tweet(
    text: str,
    use_richtext: bool = True,
    reply_to_tweet_id: Optional[Union[int, str]] = None,
) -> Dict[str, Any]:
    """
    Create a new note tweet (long-form content).

    Args:
        text: The text content of the tweet (supports markdown if use_richtext=True)
        use_richtext: Whether to enable rich text formatting using markdown
        reply_to_tweet_id: Optional tweet ID to reply to

    Returns:
        Dict containing the tweet ID and status
    """
    if twitter_client is None:
        return {
            "success": False,
            "message": "Twitter client not initialized. Check APIDANCE_API_KEY environment variable.",
        }

    try:
        # Create the note tweet
        tweet_id = twitter_client.create_note_tweet(
            text=text, use_richtext=use_richtext, reply_to_tweet_id=reply_to_tweet_id
        )

        if tweet_id:
            return {
                "success": True,
                "tweet_id": tweet_id,
                "message": "Note tweet created successfully",
            }
        else:
            return {"success": False, "message": "Failed to create note tweet"}
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "An unexpected error occurred while creating note tweet",
        }


if __name__ == "__main__":
    # Initialize the Twitter client
    initialize_client()

    # Initialize and run the server
    print("Starting Twitter MCP server...")
    mcp.run(transport="stdio")
