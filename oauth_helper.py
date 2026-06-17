#!/usr/bin/env python3
"""One-time OAuth 1.0a helper — get access tokens for a second X account.

Run this with your app's consumer key/secret. It opens a browser window
where you log in as the target account, authorize the app, and it prints
the access token + secret. Use those in your MCP config.

Usage:
    python3 oauth_helper.py <consumer_key> <consumer_secret>
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import http.server
import json
import sys
import time
import urllib.parse
import urllib.request
import uuid
import webbrowser

CALLBACK_PORT = 9876
CALLBACK_URL = f"http://127.0.0.1:{CALLBACK_PORT}/callback"

_captured: dict = {}


def _sign(method: str, url: str, params: dict, consumer_secret: str, token_secret: str = "") -> str:
    params_str = "&".join(
        f"{urllib.parse.quote(k, '')}"
        f"={urllib.parse.quote(str(v), '')}"
        for k, v in sorted(params.items())
    )
    base = f"{method}&{urllib.parse.quote(url, '')}&{urllib.parse.quote(params_str, '')}"
    key = f"{urllib.parse.quote(consumer_secret, '')}&{urllib.parse.quote(token_secret, '')}"
    return base64.b64encode(
        hmac.new(key.encode(), base.encode(), hashlib.sha1).digest()
    ).decode()


def _oauth_header(params: dict) -> str:
    return "OAuth " + ", ".join(
        f'{urllib.parse.quote(k, "")}="{urllib.parse.quote(v, "")}"'
        for k, v in sorted(params.items())
        if k.startswith("oauth_")
    )


def request_token(consumer_key: str, consumer_secret: str) -> tuple[str, str]:
    url = "https://api.twitter.com/oauth/request_token"
    oauth = {
        "oauth_consumer_key": consumer_key,
        "oauth_nonce": uuid.uuid4().hex,
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_version": "1.0",
        "oauth_callback": CALLBACK_URL,
    }
    oauth["oauth_signature"] = _sign("POST", url, oauth, consumer_secret)
    req = urllib.request.Request(url, method="POST", headers={"Authorization": _oauth_header(oauth)})
    resp = urllib.request.urlopen(req, timeout=15)
    data = dict(urllib.parse.parse_qsl(resp.read().decode()))
    return data["oauth_token"], data["oauth_token_secret"]


def access_token(consumer_key: str, consumer_secret: str, req_token: str, req_secret: str, verifier: str) -> dict:
    url = "https://api.twitter.com/oauth/access_token"
    oauth = {
        "oauth_consumer_key": consumer_key,
        "oauth_nonce": uuid.uuid4().hex,
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": req_token,
        "oauth_verifier": verifier,
        "oauth_version": "1.0",
    }
    oauth["oauth_signature"] = _sign("POST", url, oauth, consumer_secret, req_secret)
    req = urllib.request.Request(url, method="POST", headers={"Authorization": _oauth_header(oauth)})
    resp = urllib.request.urlopen(req, timeout=15)
    return dict(urllib.parse.parse_qsl(resp.read().decode()))


class CallbackHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        query = urllib.parse.urlparse(self.path).query
        params = dict(urllib.parse.parse_qsl(query))
        if "oauth_token" in params and "oauth_verifier" in params:
            _captured.update(params)
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h1>Done! You can close this tab.</h1>")
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Missing parameters")

    def log_message(self, format, *args):
        pass


def main():
    if len(sys.argv) != 3:
        print("Usage: python3 oauth_helper.py <consumer_key> <consumer_secret>")
        sys.exit(1)

    ck, cs = sys.argv[1], sys.argv[2]

    print("Requesting token...")
    req_tok, req_sec = request_token(ck, cs)

    auth_url = f"https://api.twitter.com/oauth/authorize?oauth_token={req_tok}"
    print(f"\nOpening browser — log in as the account you want to authorize.\n{auth_url}\n")
    webbrowser.open(auth_url)

    print("Waiting for callback...")
    server = http.server.HTTPServer(("127.0.0.1", CALLBACK_PORT), CallbackHandler)
    server.handle_request()

    if "oauth_verifier" not in _captured:
        print("Error: no verifier received")
        sys.exit(1)

    print("Exchanging for access token...")
    result = access_token(ck, cs, _captured["oauth_token"], req_sec, _captured["oauth_verifier"])

    print(f"\n{'='*50}")
    print(f"Account:             @{result.get('screen_name', '?')}")
    print(f"User ID:             {result.get('user_id', '?')}")
    print(f"Access Token:        {result['oauth_token']}")
    print(f"Access Token Secret: {result['oauth_token_secret']}")
    print(f"{'='*50}")
    print("\nUse these in your MCP config (with the SAME consumer key/secret).")


if __name__ == "__main__":
    main()
