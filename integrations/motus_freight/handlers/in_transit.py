"""
In-Transit Handler for Motus Freight

Polls Turvo API for En Route shipments and triggers calls
for loads within 4 hours of delivery
"""

import os
import json
import redis
import requests
from datetime import datetime, timezone
from typing import Dict, Any

from . import turvo_client
from . import turvo_utils

# Configuration
REDIS_URL = os.getenv("REDIS_URL")
MOTUS_IN_TRANSIT_WEBHOOK_URL = os.getenv("MOTUS_IN_TRANSIT_WEBHOOK_URL")
CALL_HOURS_MIN = float(os.getenv("CALL_HOURS_MIN", "3"))  # Default: 3 hours
CALL_HOURS_MAX = float(os.getenv("CALL_HOURS_MAX", "4"))  # Default: 4 hours
REDIS_TTL_DAYS = int(os.getenv("REDIS_TTL_DAYS", "2"))  # Default: 2 days

# Owner filtering (optional - leave empty to allow all owners)
ALLOWED_OWNERS = os.getenv("ALLOWED_OWNERS", "")  # Comma-separated names, e.g., "Kyle Patton,Rick Straus"
ALLOWED_OWNER_IDS = os.getenv("ALLOWED_OWNER_IDS", "")  # Comma-separated IDs, e.g., "201288,5564"

# Redis client for deduplication
redis_client = redis.from_url(REDIS_URL) if REDIS_URL else None


def check_already_called(shipment_id: int) -> bool:
    """
    Check if we've already called this shipment

    Args:
        shipment_id: Turvo shipment ID

    Returns:
        bool: True if already called, False otherwise
    """
    if not redis_client:
        return False  # No Redis, can't check

    cache_key = f"motus:in_transit:{shipment_id}"
    return redis_client.get(cache_key) is not None


def mark_as_called(shipment_id: int, load_number: str):
    """
    Mark shipment as called in Redis

    Args:
        shipment_id: Turvo shipment ID
        load_number: Load number for logging
    """
    if not redis_client:
        print(f"⚠ Redis not available, cannot mark {load_number} as called")
        return

    cache_key = f"motus:in_transit:{shipment_id}"
    cache_data = {
        "load_number": load_number,
        "called_at": datetime.now(timezone.utc).isoformat()
    }

    ttl_seconds = REDIS_TTL_DAYS * 86400
    redis_client.set(cache_key, json.dumps(cache_data), ex=ttl_seconds)

    print(f"✓ Marked {load_number} as called (TTL: {REDIS_TTL_DAYS} days)")


def check_owner_allowed(shipment: Dict[str, Any]) -> tuple[bool, str]:
    """
    Check if shipment owner is in allowed list (if filtering is enabled)

    Args:
        shipment: Full shipment details

    Returns:
        tuple: (is_allowed, owner_name)
    """
    # If no filtering configured, allow all
    if not ALLOWED_OWNERS and not ALLOWED_OWNER_IDS:
        return True, "All owners allowed"

    # Extract owner info
    customer_orders = shipment.get("customerOrder", [])
    for customer_order in customer_orders:
        if customer_order.get("deleted"):
            continue

        customer = customer_order.get("customer", {})
        owner = customer.get("owner", {})
        owner_name = owner.get("name", "")
        owner_id = str(owner.get("id", ""))

        # Check against allowed names
        if ALLOWED_OWNERS:
            allowed_names = [name.strip() for name in ALLOWED_OWNERS.split(",")]
            if owner_name in allowed_names:
                return True, owner_name

        # Check against allowed IDs
        if ALLOWED_OWNER_IDS:
            allowed_ids = [id.strip() for id in ALLOWED_OWNER_IDS.split(",")]
            if owner_id in allowed_ids:
                return True, f"{owner_name} (ID: {owner_id})"

        # Found owner but not in allowed list
        return False, f"{owner_name} (ID: {owner_id})"

    # No owner found
    return False, "No owner"


def send_webhook(payload: Dict[str, Any]) -> bool:
    """
    Send webhook to HappyRobot

    Args:
        payload: Webhook payload (batch format with multiple shipments)

    Returns:
        bool: True if successful, False otherwise
    """
    if not MOTUS_IN_TRANSIT_WEBHOOK_URL:
        print("⚠ MOTUS_IN_TRANSIT_WEBHOOK_URL not configured")
        return False

    try:
        response = requests.post(
            MOTUS_IN_TRANSIT_WEBHOOK_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )

        response.raise_for_status()
        print(f"✓ Webhook sent (HTTP {response.status_code})")
        return True

    except requests.exceptions.RequestException as e:
        print(f"✗ Webhook failed: {e}")
        return False


def sync_in_transit() -> Dict[str, Any]:
    """
    Main in-transit sync logic

    1. Get all En Route shipments from Turvo
    2. For each shipment, get full details
    3. Check if delivery is within threshold (≤ 4 hours)
    4. Check if already called (Redis dedup)
    5. Send webhook to HappyRobot
    6. Mark as called

    Returns:
        dict: Summary of execution
    """
    print("="*80)
    print("MOTUS IN-TRANSIT SYNC")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print(f"Call window: {CALL_HOURS_MIN}-{CALL_HOURS_MAX} hours until delivery")

    # Show owner filtering status
    if ALLOWED_OWNERS:
        print(f"Owner filter: {ALLOWED_OWNERS} (by name)")
    elif ALLOWED_OWNER_IDS:
        print(f"Owner filter: {ALLOWED_OWNER_IDS} (by ID)")
    else:
        print(f"Owner filter: DISABLED (all owners allowed)")

    print("="*80)

    # Step 1: Get ALL En Route shipments (status 2105) across all pages
    print("\n→ Querying ALL En Route shipments (paginating)...")
    try:
        shipments = turvo_client.list_all_shipments(status=2105)
        print(f"✓ Found {len(shipments)} En Route shipments across all pages")
    except Exception as e:
        print(f"✗ Failed to get shipments: {e}")
        return {
            "success": False,
            "error": str(e),
            "calls_made": 0
        }

    if not shipments:
        print("No En Route shipments found")
        return {
            "success": True,
            "shipments_processed": 0,
            "calls_made": 0
        }

    # Filter out invalid statuses (canceled, delivered, etc.)
    INVALID_STATUSES = [
        "2107",  # Delivered
        "2108",  # Ready for billing
        "2113",  # Canceled
        "2116",  # Route complete
        "2119",  # Tender - rejected
    ]

    initial_count = len(shipments)
    shipments = [
        s for s in shipments
        if s.get("status", {}).get("code", {}).get("key") not in INVALID_STATUSES
    ]

    if len(shipments) < initial_count:
        filtered_out = initial_count - len(shipments)
        print(f"✓ Filtered out {filtered_out} shipments (canceled/delivered/etc)")

    if not shipments:
        print("No valid shipments to process after filtering")
        return {
            "success": True,
            "shipments_processed": 0,
            "calls_made": 0
        }

    # Step 2: Process each shipment
    print(f"\n→ Processing {len(shipments)} shipments...")

    calls_to_make = []  # Collect all payloads to send in one batch
    already_called_count = 0
    skipped_count = 0
    owner_filtered_count = 0
    errors = []

    for i, shipment in enumerate(shipments, 1):
        shipment_id = shipment["id"]
        custom_id = shipment.get("customId", "Unknown")

        print(f"\n[{i}/{len(shipments)}] Load {custom_id} (ID: {shipment_id})")

        # Check deduplication first (avoid unnecessary API call)
        if check_already_called(shipment_id):
            print(f"  ○ Already called, skipping")
            already_called_count += 1
            continue

        # Get full details
        try:
            details = turvo_client.get_shipment_details(shipment_id)
        except Exception as e:
            print(f"  ✗ Failed to get details: {e}")
            errors.append({"load": custom_id, "error": str(e)})
            continue

        # Check owner filtering
        is_allowed, owner_info = check_owner_allowed(details)
        if not is_allowed:
            print(f"  ○ Owner not in allowed list: {owner_info}, skipping")
            owner_filtered_count += 1
            continue

        # Transform to webhook payload
        payload = turvo_utils.transform_shipment_for_webhook(details)

        if not payload:
            # Missing critical data (logged by transform function)
            skipped_count += 1
            continue

        hours_until = payload["delivery"]["hours_until"]

        # Check if within call window (3-4 hours)
        if hours_until is None:
            print(f"  ○ No ETA available, skipping")
            skipped_count += 1
            continue

        if hours_until < CALL_HOURS_MIN or hours_until > CALL_HOURS_MAX:
            print(f"  ○ {hours_until}h until delivery (outside {CALL_HOURS_MIN}-{CALL_HOURS_MAX}h window), skipping")
            skipped_count += 1
            continue

        # Within call window - add to batch!
        print(f"  ✓ {hours_until}h until delivery - WILL CALL")
        print(f"    Driver: {payload['driver']['name']} ({payload['driver']['phone']})")
        print(f"    Delivering to: {payload['delivery']['location']['city']}, {payload['delivery']['location']['state']}")
        print(f"    ETA: {payload['delivery']['eta_formatted']}")

        if payload['equipment']['temperature']:
            print(f"    Temperature: {payload['equipment']['temperature']}°{payload['equipment']['temp_units']}")

        # Add to batch
        calls_to_make.append({
            "shipment_id": shipment_id,
            "load_number": custom_id,
            "payload": payload
        })

    # Step 3: Send all calls in one batch webhook
    if calls_to_make:
        print(f"\n→ Sending batch webhook with {len(calls_to_make)} calls...")

        # Prepare batch payload
        batch_payload = {
            "shipments": [call["payload"] for call in calls_to_make],
            "total_calls": len(calls_to_make),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # Send the batch
        if send_webhook(batch_payload):
            print(f"✓ Batch webhook sent successfully")
            # Mark all as called
            for call in calls_to_make:
                mark_as_called(call["shipment_id"], call["load_number"])
        else:
            errors.append({"error": "Batch webhook failed", "loads": [call["load_number"] for call in calls_to_make]})

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Total shipments: {len(shipments)}")
    print(f"Already called: {already_called_count}")
    print(f"Owner filtered: {owner_filtered_count}")
    print(f"Skipped (not in threshold or missing data): {skipped_count}")
    print(f"Calls triggered: {len(calls_to_make)}")

    if errors:
        print(f"\nErrors ({len(errors)}):")
        for error in errors:
            print(f"  - {error}")

    return {
        "success": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "shipments_total": len(shipments),
        "shipments_processed": len(shipments),
        "already_called": already_called_count,
        "owner_filtered": owner_filtered_count,
        "skipped": skipped_count,
        "calls_made": len(calls_to_make),
        "errors": errors
    }
