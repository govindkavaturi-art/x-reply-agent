import requests

from agent.config import X_API_BEARER_TOKEN

BASE_URL = "https://api.twitter.com/2"


def _headers():
    return {"Authorization": f"Bearer {X_API_BEARER_TOKEN}"}


def search_recent(query: str, start_time: str, max_results: int = 30) -> dict:
    """Search recent tweets. Returns raw API response JSON."""
    resp = requests.get(
        f"{BASE_URL}/tweets/search/recent",
        headers=_headers(),
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
        headers=_headers(),
        params={
            "tweet.fields": "created_at,in_reply_to_user_id,referenced_tweets",
            "exclude": "retweets",
            "start_time": start_time,
            "max_results": 100,
        },
    )
    resp.raise_for_status()
    return resp.json()
