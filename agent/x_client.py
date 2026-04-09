import requests
from requests_oauthlib import OAuth1

from agent.config import (
    X_CONSUMER_KEY,
    X_CONSUMER_SECRET,
    X_ACCESS_TOKEN,
    X_ACCESS_TOKEN_SECRET,
)

BASE_URL = "https://api.twitter.com/2"


def _auth():
    return OAuth1(
        X_CONSUMER_KEY,
        X_CONSUMER_SECRET,
        X_ACCESS_TOKEN,
        X_ACCESS_TOKEN_SECRET,
        signature_method="HMAC-SHA1",
    )


def search_recent(query: str, start_time: str, max_results: int = 30) -> dict:
    """Search recent tweets. Returns raw API response JSON."""
    resp = requests.get(
        f"{BASE_URL}/tweets/search/recent",
        auth=_auth(),
        params={
            "query": query,
            "max_results": min(max_results, 100),
            "tweet.fields": "created_at,public_metrics,lang,author_id",
            "user.fields": "username,public_metrics,created_at",
            "expansions": "author_id",
            "start_time": start_time,
        },
    )
    resp.raise_for_status()
    return resp.json()


def get_user_tweets(user_id: str, start_time: str) -> dict:
    """Fetch a user's recent tweets (excluding retweets)."""
    resp = requests.get(
        f"{BASE_URL}/users/{user_id}/tweets",
        auth=_auth(),
        params={
            "tweet.fields": "created_at,in_reply_to_user_id,referenced_tweets",
            "exclude": "retweets",
            "start_time": start_time,
            "max_results": 100,
        },
    )
    resp.raise_for_status()
    return resp.json()
