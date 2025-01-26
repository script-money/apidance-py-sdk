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

    # Example: Get followers you know
    following = client.get_followers_you_know(user_id="1880358740152709121", count=30)
    print(f"\nFound {len(following)} followers you know:")
    for user in following:
        print(user.username)

    # Example: Create note tweet, requires Premium+
    long_text = """
This is a test tweet to check the length, formatting, and overall look of a longer tweet. I want to see how it appears on different devices and if there are any unexpected line breaks or display issues.

I'm also testing the use of hashtags and mentions. Will they work correctly and improve *discoverability*? Let's find out! #TestTweet @YourAccount

This tweet includes a question to **encourage engagement**. Are people more likely to respond or interact with a longer tweet that asks a question?

Finally, I'm adding a few more sentences to reach the desired word count and see how the tweet handles a variety of sentence lengths and structures.  What do you think of longer-form content on Twitter? Does it have a place? Let me know your thoughts!  Testing, testing, 1, 2, 3! Just a few more words now. This is the end.
    """
    note_tweet_id = client.create_note_tweet(
        text=long_text,
        use_richtext=True,
        reply_to_tweet_id="1859428851736248469",
    )
    print(f"New note tweet created successfully with ID: {note_tweet_id}")


if __name__ == "__main__":
    example_twitter_client()
