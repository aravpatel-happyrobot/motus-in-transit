# Token Caching Strategy

## The Problem

The Turvo access token is valid for **12 hours** (`expires_in: 43198` seconds).

**Current inefficient approach:**
```python
Every 15 minutes:
  → Authenticate (get new token)  ← WASTEFUL!
  → Query shipments
```

This wastes API calls and adds ~1 second to every poll.

---

## The Solution: Cache the Token

**Efficient approach:**
```python
On first run:
  → Authenticate
  → Cache token + expiration time

Every 15 minutes:
  → Check if token expired
  → If expired: re-authenticate and cache new token
  → If valid: use cached token
  → Query shipments
```

---

## Implementation

### Option 1: In-Memory Cache (Simple)

```python
# Global variables
cached_token = None
token_expires_at = None

def get_turvo_token():
    """Get cached token or fetch new one if expired"""
    global cached_token, token_expires_at

    # Check if we have a valid cached token
    if cached_token and token_expires_at:
        now = datetime.now(timezone.utc)
        if now < token_expires_at:
            print("Using cached token")
            return cached_token

    # Token expired or doesn't exist, fetch new one
    print("Fetching new token...")
    response = requests.post(
        f"{TURVO_BASE_URL}/oauth/token",
        headers={
            "Content-Type": "application/json",
            "x-api-key": TURVO_API_KEY
        },
        json={
            "grant_type": "password",
            "username": TURVO_USERNAME,
            "password": TURVO_PASSWORD,
            "client_id": "publicapi",
            "client_secret": "secret",
            "scope": "read+trust+write",
            "type": "business"
        }
    )

    data = response.json()
    cached_token = data["access_token"]
    expires_in = data["expires_in"]  # 43198 seconds (~12 hours)

    # Set expiration with 5-minute buffer
    token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in - 300)

    print(f"New token cached, expires at {token_expires_at}")
    return cached_token
```

**Pros:**
- Simple to implement
- No external dependencies
- Fast

**Cons:**
- Token lost if server restarts
- Not shared across multiple instances

---

### Option 2: Redis Cache (Production-Ready)

```python
import redis
import json
from datetime import datetime, timezone, timedelta

redis_client = redis.from_url(os.getenv("REDIS_URL"))

def get_turvo_token():
    """Get cached token from Redis or fetch new one"""

    # Try to get from Redis
    cached_data = redis_client.get("turvo:auth_token")

    if cached_data:
        token_data = json.loads(cached_data)
        expires_at = datetime.fromisoformat(token_data["expires_at"])

        if datetime.now(timezone.utc) < expires_at:
            print("Using cached token from Redis")
            return token_data["access_token"]

    # Token expired or doesn't exist, fetch new one
    print("Fetching new token...")
    response = requests.post(
        f"{TURVO_BASE_URL}/oauth/token",
        headers={
            "Content-Type": "application/json",
            "x-api-key": TURVO_API_KEY
        },
        json={
            "grant_type": "password",
            "username": TURVO_USERNAME,
            "password": TURVO_PASSWORD,
            "client_id": "publicapi",
            "client_secret": "secret",
            "scope": "read+trust+write",
            "type": "business"
        }
    )

    data = response.json()
    access_token = data["access_token"]
    expires_in = data["expires_in"]

    # Calculate expiration (with 5-minute buffer)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in - 300)

    # Cache in Redis
    token_data = {
        "access_token": access_token,
        "expires_at": expires_at.isoformat()
    }

    # Set with TTL slightly longer than actual expiration
    redis_client.set(
        "turvo:auth_token",
        json.dumps(token_data),
        ex=expires_in  # Redis will auto-delete when expired
    )

    print(f"New token cached in Redis, expires at {expires_at}")
    return access_token
```

**Pros:**
- Survives server restarts
- Shared across multiple instances (if you scale horizontally)
- Uses existing Redis infrastructure

**Cons:**
- Slightly more complex
- Requires Redis connection

---

## Why 5-Minute Buffer?

```python
expires_at = now + timedelta(seconds=expires_in - 300)
#                                                  ^^^
#                                               5 minutes
```

**Without buffer:**
- Token expires at exactly 12:00:00
- Request sent at 11:59:59 → Uses token
- Token becomes invalid at 12:00:00 during request
- Request fails

**With 5-minute buffer:**
- Token cached until 11:55:00
- At 11:55:01 → Fetch new token
- No risk of using expired token mid-request

---

## Performance Comparison

### Without Caching (Current)
```
Poll #1: Auth (1s) + Query (4s) = 5s
Poll #2: Auth (1s) + Query (4s) = 5s  ← Wasteful!
Poll #3: Auth (1s) + Query (4s) = 5s  ← Wasteful!
...
48 polls/day × 1s auth = 48 seconds wasted
```

### With Caching (Recommended)
```
Poll #1: Auth (1s) + Query (4s) = 5s
Poll #2: Cache hit (0s) + Query (4s) = 4s  ← Faster!
Poll #3: Cache hit (0s) + Query (4s) = 4s  ← Faster!
...
47 polls/day × 0s auth = 0 seconds wasted
```

**Daily savings:**
- 47 unnecessary auth calls eliminated
- ~47 seconds of API time saved
- Reduced load on Turvo's auth server

---

## Recommended Implementation

**Use Redis caching** because:
1. You already have Redis for deduplication
2. Survives restarts
3. Scalable if you add more workers

**Code structure:**
```python
# handlers/turvo_client.py

import os
import json
import redis
import requests
from datetime import datetime, timezone, timedelta

REDIS_URL = os.getenv("REDIS_URL")
TURVO_BASE_URL = os.getenv("TURVO_BASE_URL")
TURVO_API_KEY = os.getenv("TURVO_API_KEY")
TURVO_USERNAME = os.getenv("TURVO_USERNAME")
TURVO_PASSWORD = os.getenv("TURVO_PASSWORD")

redis_client = redis.from_url(REDIS_URL)

def get_turvo_token():
    """Get cached Turvo access token or fetch new one if expired"""

    # Try Redis cache first
    cached_data = redis_client.get("turvo:auth_token")

    if cached_data:
        token_data = json.loads(cached_data)
        expires_at = datetime.fromisoformat(token_data["expires_at"])

        if datetime.now(timezone.utc) < expires_at:
            return token_data["access_token"]

    # Fetch new token
    response = requests.post(
        f"{TURVO_BASE_URL}/oauth/token",
        headers={
            "Content-Type": "application/json",
            "x-api-key": TURVO_API_KEY
        },
        json={
            "grant_type": "password",
            "username": TURVO_USERNAME,
            "password": TURVO_PASSWORD,
            "client_id": "publicapi",
            "client_secret": "secret",
            "scope": "read+trust+write",
            "type": "business"
        },
        timeout=10
    )

    response.raise_for_status()
    data = response.json()

    access_token = data["access_token"]
    expires_in = data["expires_in"]

    # Cache with 5-minute buffer
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in - 300)

    redis_client.set(
        "turvo:auth_token",
        json.dumps({
            "access_token": access_token,
            "expires_at": expires_at.isoformat()
        }),
        ex=expires_in
    )

    return access_token

def turvo_get(endpoint, params=None):
    """Make authenticated GET request to Turvo API"""
    token = get_turvo_token()

    response = requests.get(
        f"{TURVO_BASE_URL}{endpoint}",
        headers={
            "Authorization": f"Bearer {token}",
            "x-api-key": TURVO_API_KEY,
            "Content-Type": "application/json"
        },
        params=params,
        timeout=30
    )

    response.raise_for_status()
    return response.json()
```

---

## Token Refresh vs. Re-authentication

**Turvo provides a `refresh_token`** in the auth response:
```json
{
  "access_token": "3b_-06ff...",
  "refresh_token": "81db8ffd-...",
  "expires_in": 43198
}
```

**Should we use it?**

**Option A: Just re-authenticate (Simpler)**
- When token expires, call `/oauth/token` again with username/password
- Pros: Simple, no refresh logic needed
- Cons: Slightly more API calls

**Option B: Use refresh token (More complex)**
- When token expires, call `/oauth/token` with `grant_type=refresh_token`
- Pros: Slightly fewer auth server hits
- Cons: More complex logic, need to cache refresh token too

**Recommendation: Option A (re-authenticate)**
- Token lasts 12 hours
- You poll every 15 minutes = 2 re-auths per day
- Not worth the complexity

---

## Summary

**✅ DO:**
- Cache the token in Redis
- Use 5-minute expiration buffer
- Re-authenticate when expired

**❌ DON'T:**
- Re-authenticate on every poll
- Use refresh tokens (unnecessary complexity)
- Store credentials in Redis (only store token)

**Result:**
- 47 fewer auth calls per day
- Faster polls (4s instead of 5s)
- More efficient API usage

---

**Last Updated:** 2026-01-02
