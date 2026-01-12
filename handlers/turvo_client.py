"""
Turvo API Client with OAuth2 authentication and token caching
"""

import os
import json
import redis
import requests
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

# Configuration
REDIS_URL = os.getenv("REDIS_URL")
TURVO_BASE_URL = os.getenv("TURVO_BASE_URL", "https://publicapi.turvo.com/v1")
TURVO_API_KEY = os.getenv("TURVO_API_KEY")
TURVO_USERNAME = os.getenv("TURVO_USERNAME")
TURVO_PASSWORD = os.getenv("TURVO_PASSWORD")

# Redis client for token caching
redis_client = redis.from_url(REDIS_URL) if REDIS_URL else None


def get_turvo_token() -> str:
    """
    Get cached Turvo access token or fetch new one if expired

    Token is cached in Redis with 12-hour expiration (with 5-min buffer)

    Returns:
        str: Valid access token
    """
    # Try Redis cache first
    if redis_client:
        cached_data = redis_client.get("019b0e1e-f561-7a0a-97a4-11058661c03e:auth_token")

        if cached_data:
            try:
                token_data = json.loads(cached_data)
                expires_at = datetime.fromisoformat(token_data["expires_at"])

                if datetime.now(timezone.utc) < expires_at:
                    return token_data["access_token"]
            except (json.JSONDecodeError, KeyError, ValueError):
                pass  # Invalid cache, fetch new token

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
    expires_in = data["expires_in"]  # ~43198 seconds (12 hours)

    # Cache with 5-minute buffer to avoid expiration mid-request
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in - 300)

    if redis_client:
        redis_client.set(
            "019b0e1e-f561-7a0a-97a4-11058661c03e:auth_token",
            json.dumps({
                "access_token": access_token,
                "expires_at": expires_at.isoformat()
            }),
            ex=expires_in
        )

    return access_token


def turvo_get(endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Make authenticated GET request to Turvo API

    Args:
        endpoint: API endpoint (e.g., "/shipments/list")
        params: Query parameters

    Returns:
        dict: JSON response from API
    """
    token = get_turvo_token()

    url = f"{TURVO_BASE_URL}{endpoint}"

    response = requests.get(
        url,
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


def list_shipments(status: Optional[int] = None, page_size: int = 100, start: int = 0) -> Dict[str, Any]:
    """
    Get list of shipments with optional status filter

    Args:
        status: Status code (e.g., 2105 for En Route)
        page_size: Number of results per page
        start: Starting index for pagination

    Returns:
        dict: Response with 'shipments' and 'pagination' keys
    """
    params = {"pageSize": page_size}

    if status:
        params["status[eq]"] = status

    if start > 0:
        params["start"] = start

    response = turvo_get("/shipments/list", params)
    details = response.get("details", {})

    return {
        "shipments": details.get("shipments", []),
        "pagination": details.get("pagination", {})
    }


def list_all_shipments(status: Optional[int] = None) -> list:
    """
    Get ALL shipments across all pages

    Args:
        status: Status code (e.g., 2105 for En Route)

    Returns:
        list: Array of all shipment objects
    """
    all_shipments = []
    start = 0
    page_num = 0

    while True:
        result = list_shipments(status=status, page_size=100, start=start)
        shipments = result["shipments"]
        pagination = result["pagination"]

        all_shipments.extend(shipments)

        if not pagination.get("moreAvailable"):
            break

        # Next page
        start += len(shipments)
        page_num += 1

        # Safety limit to prevent infinite loops
        if page_num >= 100:
            break

    return all_shipments


def get_shipment_details(shipment_id: int) -> Dict[str, Any]:
    """
    Get full details for a specific shipment

    Args:
        shipment_id: Turvo shipment ID

    Returns:
        dict: Full shipment object with globalRoute, drivers, etc.
    """
    response = turvo_get(f"/shipments/{shipment_id}")
    return response.get("details", {})


def get_user_details(user_id: int) -> Dict[str, Any]:
    """
    Get user details by ID (for owner contact info)

    Args:
        user_id: Turvo user ID

    Returns:
        dict: User object with name, email, phone, etc.
    """
    response = turvo_get(f"/users/{user_id}")
    return response.get("details", {})
