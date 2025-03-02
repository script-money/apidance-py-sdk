# Apidance SDK

A Python SDK for interacting with the Apidance API (https://apidance.pro/).

## Installation

```bash
pip install apidance
```

## Configuration

Create a `.env` file in your project root with your API credentials:

```env
APIDANCE_API_KEY=your_api_key_here
X_AUTH_TOKEN=your_x_auth_token_here  # Required for reply/like actions
```

Get your API key from [https://apidance.pro](https://apidance.pro)

You can find your `X_AUTH_TOKEN` in your browser cookies when logged into x.com:
1. Open x.com and log in
2. Open browser developer tools (F12 or right-click -> Inspect)
3. Go to Application/Storage -> Cookies -> x.com
4. Find and copy the value of `auth_token`

Or provide the credentials directly when initializing the client:

```python
client = TwitterClient(
    api_key="your_api_key_here",
    auth_token="your_auth_token_here"  # Required for reply/like actions
)
```

## Usage

> Check out the [examples](https://github.com/script-money/apidance/tree/main/examples)

```python
from apidance import TwitterClient

# Initialize the client
client = TwitterClient()

# Search tweets
tweets = client.search_timeline(
    query="python",
)

# Get user information
user = client.get_user_by_screen_name("example")

users = client.get_following(user_id=user["id"])

# Get tweets from a list
list_tweets = client.get_list_latest_tweets(
    list_id="your_list_id",
)

# Reply to a tweet
client.create_tweet(
    text="Your reply text",
    reply_to_tweet_id="tweet_id_to_reply_to",
)

# Like a tweet
client.favorite_tweet(tweet_id="tweet_id_to_like")
```

## MCP server

FillSet config file
```json
{
    "mcpServers": {
        "apidance": {
            "command": "/path/to/uv",
            "args": [
                "--directory",
                "/path/to/apidance-sdk",
                "run",
                "mcp_server.py"
            ]
        }
    }
}
```

## Features

- Search Twitter timeline with various filters (Latest, Top, People, Photos, Videos)
- Get detailed user information by screen name
- Fetch tweets from Twitter lists
- Search Following
- Reply to tweets (requires auth_token)
- Like tweets (requires auth_token)
- Create tweets and reply to existing tweets
- Create note tweets (long rich text tweet, requires Premium+)
- Host as mcp server

## Models

The SDK provides two main data models:

- `Tweet`: Represents a Twitter post with all its metadata
- `User`: Contains detailed user information including profile data, stats, and verification status

## License

MIT License
