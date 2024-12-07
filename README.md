# Apidance SDK

A Python SDK for interacting with the Apidance API (https://apidance.pro/).

## Installation

```bash
pip install apidance-sdk
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

# Get tweets from a list
list_tweets = client.get_list_latest_tweets(
    list_id="your_list_id",
)
```

## Features

- Search Twitter timeline with various filters (Latest, Top, People, Photos, Videos)
- Get detailed user information by screen name
- Fetch tweets from Twitter lists
- Automatic rate limit handling and retries
- Type hints and data models for better development experience

## Models

The SDK provides two main data models:

- `Tweet`: Represents a Twitter post with all its metadata
- `User`: Contains detailed user information including profile data, stats, and verification status

## Error Handling

The SDK includes built-in error handling for:
- Rate limiting with automatic retries
- Connection timeouts
- API response validation

## License

MIT License
