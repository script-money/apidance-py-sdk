import os

from apidance.client import TwitterClient

api_key = os.getenv("APIDANCE_API_KEY")


def example_twitter_client():
    """Example of how to use the TwitterClient."""
    # Initialize the client with your API key
    # You can also set APIDANCE_API_KEY environment variable
    client = TwitterClient(api_key=api_key)

    # Example: Get user info
    user_info = client.get_user_by_screen_name(screen_name="AICell_World")
    print(f"User info: {user_info}")

    # Example: Get user tweets
    tweets = client.get_user_tweets(user_id=user_info.id, count=20)
    print(f"\nFound {len(tweets)} tweets:")
    print(tweets[0])

    # Example: Get tweet
    result = client.tweet_result_by_rest_id(tweets[0].id)
    print(result)

    # Example: Favorite tweet
    client.favorite_tweet(tweets[0].id)

    # Example: Reply to tweet
    client.create_tweet(
        text="You are geniuses! Are you? @OverlordBot_",
        reply_to_tweet_id="1877189985620639945",
    )

    # Example: Get user following
    users = client.get_following(user_id=user_info.id)
    user_handles = [user.username for user in users]
    print(f"\nFound {len(user_handles)} users:")
    print(user_handles)

    # Example: Search tweets
    search_results = client.search_timeline(
        query="BTC from:CryptoPainter_X since:2024-11-22 until:2024-11-23 min_faves:1",
    )
    print(f"\nFound {len(search_results)} tweets:")
    print(search_results)

    # Example: Search List
    list_tweets = client.get_list_latest_tweets(list_id="1729067517866586475")
    print(f"\nFound {len(list_tweets)} tweets:")
    print(list_tweets[0])

    # Example: Get followers
    followers = client.get_followers(user_id="44196397", count=30)
    print(f"\nFound {len(followers)} followers")
    for follower in followers:
        print(follower)


if __name__ == "__main__":
    example_twitter_client()
