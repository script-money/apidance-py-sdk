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
```

Or provide the API key directly when initializing the client:

```python
client = TwitterClient(api_key="your_api_key_here")
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
```

## Features

- Search Twitter timeline with various filters (Latest, Top, People, Photos, Videos)
- Get detailed user information by screen name
- Fetch tweets from Twitter lists
- Search Following

## Models

The SDK provides two main data models:

- `Tweet`: Represents a Twitter post with all its metadata
- `User`: Contains detailed user information including profile data, stats, and verification status

## License

MIT License
