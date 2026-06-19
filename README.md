# x-mcp

A minimal, dependency-free MCP server for the X (Twitter) API v2. Built because every existing one was broken.

## Why

We tried the popular Twitter MCP servers. They all failed with output schema validation errors in Claude Code. So we built one that works — zero external dependencies, pure stdlib + the MCP SDK.

## Tools

| Tool | Description |
|------|-------------|
| `get_me` | Authenticated user profile |
| `get_user_profile` | Public profile by username |
| `post_tweet` | Post a tweet (with optional reply) |
| `search_tweets` | Search recent tweets |
| `get_user_tweets` | Recent tweets from a user |
| `get_timeline` | Home timeline (reverse chronological) |
| `delete_tweet` | Delete a tweet by ID |

## Setup

### 1. Get X API credentials

Go to [console.x.com](https://console.x.com), create a project and app, set permissions to **Read and Write**, generate OAuth 1.0a credentials.

You need four values:
- API Key (Consumer Key)
- API Secret Key (Consumer Secret)
- Access Token (format: `123456789-AbCdEf...`)
- Access Token Secret

### 2. Register with Claude Code

```bash
claude mcp add twitter \
  -e API_KEY=your_api_key \
  -e API_SECRET_KEY=your_api_secret \
  -e ACCESS_TOKEN=your_access_token \
  -e ACCESS_TOKEN_SECRET=your_access_token_secret \
  -s user -- python3 /path/to/x-mcp/server.py
```

### 3. Restart Claude Code

The seven tools appear automatically. No configuration beyond the credentials.

### Optional: use Xquik for search

`search_tweets` can use the Xquik API instead of the X API recent search endpoint.
Set these variables in addition to your normal server command:

- `X_SEARCH_BACKEND=xquik`
- `XQUIK_API_KEY=your_xquik_api_key`
- `XQUIK_BASE_URL=https://xquik.com/api/v1` (optional)

This only changes `search_tweets`. Profile, timeline, post, and delete tools keep
using the OAuth 1.0a X API credentials above.

## Requirements

- Python 3.9+
- `mcp` package (`pip install mcp`)
- X API pay-per-use tier ($5 minimum credit, no subscription needed)

## Multiple accounts

Register the same server with different credentials for each account:

```bash
claude mcp add twitter-personal -e API_KEY=... -- python3 server.py
claude mcp add twitter-brand -e API_KEY=... -- python3 server.py
```

## License

MIT - [The Funkatorium](https://github.com/funkatorium)
