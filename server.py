#!/opt/homebrew/bin/python3.11
"""X (Twitter) MCP server — OAuth 1.0a, X API v2, FastMCP."""

import base64
import hashlib
import hmac
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

from mcp.server.fastmcp import FastMCP

_REQUIRED_ENV = ("API_KEY", "API_SECRET_KEY", "ACCESS_TOKEN", "ACCESS_TOKEN_SECRET")
_missing = [k for k in _REQUIRED_ENV if not os.environ.get(k)]
X_SEARCH_BACKEND = os.environ.get("X_SEARCH_BACKEND", "x").lower()
XQUIK_API_KEY = os.environ.get("XQUIK_API_KEY")
XQUIK_BASE_URL = os.environ.get("XQUIK_BASE_URL", "https://xquik.com/api/v1").rstrip("/")
if _missing and X_SEARCH_BACKEND != "xquik":
    raise RuntimeError(f"Missing required environment variables: {', '.join(_missing)}")
if X_SEARCH_BACKEND == "xquik" and not XQUIK_API_KEY:
    raise RuntimeError("Missing required environment variable: XQUIK_API_KEY")

API_KEY = os.environ.get("API_KEY", "")
API_SECRET_KEY = os.environ.get("API_SECRET_KEY", "")
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN", "")
ACCESS_TOKEN_SECRET = os.environ.get("ACCESS_TOKEN_SECRET", "")

BASE_URL = "https://api.twitter.com"

mcp = FastMCP("x-mcp")


def _oauth_request(method, url, body=None, params=None):
    if _missing:
        return {
            "error": "Missing required environment variables",
            "detail": ", ".join(_missing),
        }

    oauth_params = {
        "oauth_consumer_key": API_KEY,
        "oauth_nonce": uuid.uuid4().hex,
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": ACCESS_TOKEN,
        "oauth_version": "1.0",
    }

    all_params = {**oauth_params}
    if params:
        all_params.update(params)

    params_str = "&".join(
        f'{urllib.parse.quote(k, "")}'
        f'={urllib.parse.quote(str(v), "")}'
        for k, v in sorted(all_params.items())
    )
    base_string = (
        f'{method}&{urllib.parse.quote(url, "")}&{urllib.parse.quote(params_str, "")}'
    )
    signing_key = (
        f'{urllib.parse.quote(API_SECRET_KEY, "")}'
        f'&{urllib.parse.quote(ACCESS_TOKEN_SECRET, "")}'
    )
    signature = base64.b64encode(
        hmac.new(signing_key.encode(), base_string.encode(), hashlib.sha1).digest()
    ).decode()
    oauth_params["oauth_signature"] = signature

    auth_header = "OAuth " + ", ".join(
        f'{urllib.parse.quote(k, "")}="{urllib.parse.quote(v, "")}"'
        for k, v in sorted(oauth_params.items())
    )

    req_url = url
    if params and method == "GET":
        req_url += "?" + urllib.parse.urlencode(params)

    req = urllib.request.Request(req_url, method=method, headers={"Authorization": auth_header})
    if body:
        req.add_header("Content-Type", "application/json")
        req.data = json.dumps(body).encode()

    try:
        resp = urllib.request.urlopen(req)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try:
            detail = json.loads(e.read())
        except Exception:
            detail = e.reason
        return {"error": f"HTTP {e.code}", "detail": detail}
    except urllib.error.URLError as e:
        return {"error": "Network error", "detail": str(e.reason)}


def _xquik_request(path, params=None):
    if not XQUIK_API_KEY:
        return {"error": "Missing required environment variable", "detail": "XQUIK_API_KEY"}

    req_url = f"{XQUIK_BASE_URL}{path}"
    if params:
        req_url += "?" + urllib.parse.urlencode(params)

    req = urllib.request.Request(
        req_url,
        method="GET",
        headers={"Accept": "application/json", "x-api-key": XQUIK_API_KEY},
    )

    try:
        resp = urllib.request.urlopen(req)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try:
            detail = json.loads(e.read())
        except Exception:
            detail = e.reason
        return {"error": f"HTTP {e.code}", "detail": detail}
    except urllib.error.URLError as e:
        return {"error": "Network error", "detail": str(e.reason)}


@mcp.tool()
def get_me() -> dict:
    """Return the authenticated user's profile."""
    return _oauth_request("GET", f"{BASE_URL}/2/users/me")


@mcp.tool()
def get_user_profile(username: str) -> dict:
    """Return a user's public profile by username."""
    url = f"{BASE_URL}/2/users/by/username/{urllib.parse.quote(username, '')}"
    params = {
        "user.fields": "description,public_metrics,pinned_tweet_id,profile_image_url"
    }
    return _oauth_request("GET", url, params=params)


@mcp.tool()
def post_tweet(text: str, reply_to_tweet_id: str | None = None) -> dict:
    """Post a tweet. Optionally reply to an existing tweet by ID."""
    body: dict = {"text": text}
    if reply_to_tweet_id:
        body["reply"] = {"in_reply_to_tweet_id": reply_to_tweet_id}
    return _oauth_request("POST", f"{BASE_URL}/2/tweets", body=body)


@mcp.tool()
def search_tweets(query: str, max_results: int = 10) -> dict:
    """Search recent tweets matching a query."""
    if X_SEARCH_BACKEND == "xquik":
        return _xquik_request(
            "/x/tweets/search",
            params={"q": query, "limit": str(max_results)},
        )

    params = {
        "query": query,
        "max_results": str(max_results),
        "tweet.fields": "created_at,public_metrics,author_id",
    }
    return _oauth_request("GET", f"{BASE_URL}/2/tweets/search/recent", params=params)


@mcp.tool()
def get_user_tweets(username: str, max_results: int = 10) -> dict:
    """Return recent tweets from a user by username."""
    user_resp = _oauth_request(
        "GET", f"{BASE_URL}/2/users/by/username/{urllib.parse.quote(username, '')}"
    )
    if "error" in user_resp:
        return user_resp
    try:
        user_id = user_resp["data"]["id"]
    except (KeyError, TypeError):
        return {"error": "Could not resolve user ID", "detail": user_resp}

    params = {
        "max_results": str(max_results),
        "tweet.fields": "created_at,public_metrics",
    }
    return _oauth_request("GET", f"{BASE_URL}/2/users/{user_id}/tweets", params=params)


@mcp.tool()
def get_timeline(max_results: int = 10) -> dict:
    """Return the authenticated user's reverse-chronological home timeline."""
    me_resp = _oauth_request("GET", f"{BASE_URL}/2/users/me")
    if "error" in me_resp:
        return me_resp
    try:
        my_id = me_resp["data"]["id"]
    except (KeyError, TypeError):
        return {"error": "Could not resolve own user ID", "detail": me_resp}

    params = {
        "max_results": str(max_results),
        "tweet.fields": "created_at,public_metrics,author_id",
    }
    return _oauth_request(
        "GET",
        f"{BASE_URL}/2/users/{my_id}/timelines/reverse_chronological",
        params=params,
    )


@mcp.tool()
def delete_tweet(tweet_id: str) -> dict:
    """Delete a tweet by ID."""
    return _oauth_request("DELETE", f"{BASE_URL}/2/tweets/{urllib.parse.quote(tweet_id, '')}")


if __name__ == "__main__":
    mcp.run()
