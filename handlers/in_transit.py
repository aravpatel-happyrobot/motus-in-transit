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
REDIS_TTL_DAYS = int(os.getenv("REDIS_TTL_DAYS", "2"))  # Default: 2 days

# Two-window call system
# Window 1: Check-in call (3-4 hours before delivery)
CALL_WINDOW_1_MIN = float(os.getenv("CALL_WINDOW_1_MIN", "3"))
CALL_WINDOW_1_MAX = float(os.getenv("CALL_WINDOW_1_MAX", "4"))
# Window 2: Final call (0-30 minutes before delivery)
CALL_WINDOW_2_MIN = float(os.getenv("CALL_WINDOW_2_MIN", "0"))
CALL_WINDOW_2_MAX = float(os.getenv("CALL_WINDOW_2_MAX", "0.5"))

# Owner filtering (optional - leave empty to allow all owners)
ALLOWED_OWNERS = os.getenv("ALLOWED_OWNERS", "")  # Comma-separated names, e.g., "Kyle Patton,Rick Straus"
ALLOWED_OWNER_IDS = os.getenv("ALLOWED_OWNER_IDS", "")  # Comma-separated IDs, e.g., "201288,5564"

# Redis client for deduplication
redis_client = redis.from_url(REDIS_URL) if REDIS_URL else None


def get_overnight_date_key() -> str:
    """
    Get the date key for overnight deduplication

    Overnight spans 6 PM to 8 AM, so:
    - 6 PM - 11:59 PM on Jan 15 → "2026-01-15"
    - 12 AM - 7:59 AM on Jan 16 → still "2026-01-15" (same overnight period)

    Returns:
        str: Date string for the overnight period (YYYY-MM-DD)
    """
    now_est = datetime.now(turvo_utils.EST_TIMEZONE)

    # If it's after midnight but before 8 AM, we're still in "yesterday's" overnight
    if now_est.hour < turvo_utils.OVERNIGHT_END_HOUR:
        # Subtract a day to get the overnight period date
        from datetime import timedelta
        overnight_date = (now_est - timedelta(days=1)).date()
    else:
        overnight_date = now_est.date()

    return overnight_date.isoformat()


def check_already_called(shipment_id: int, call_type: str) -> bool:
    """
    Check if we've already made this specific call type for this shipment

    Args:
        shipment_id: Turvo shipment ID
        call_type: "checkin", "final", or "late_check"

    Returns:
        bool: True if already called, False otherwise
    """
    if not redis_client:
        return False  # No Redis, can't check

    # For late_check, include the overnight date so it resets each night
    if call_type == "late_check":
        overnight_date = get_overnight_date_key()
        cache_key = f"019b0e1e-f561-7a0a-97a4-11058661c03e:in_transit:{call_type}:{overnight_date}:{shipment_id}"
    else:
        cache_key = f"019b0e1e-f561-7a0a-97a4-11058661c03e:in_transit:{call_type}:{shipment_id}"

    return redis_client.get(cache_key) is not None


def mark_as_called(shipment_id: int, load_number: str, call_type: str, minutes_late: float = None):
    """
    Mark specific call type as completed for this shipment

    Args:
        shipment_id: Turvo shipment ID
        load_number: Load number for logging
        call_type: "checkin", "final", or "late_check"
        minutes_late: For late_check, how many minutes late the driver was
    """
    if not redis_client:
        print(f"⚠ Redis not available, cannot mark {load_number} as called")
        return

    # For late_check, include the overnight date so it resets each night
    if call_type == "late_check":
        overnight_date = get_overnight_date_key()
        cache_key = f"019b0e1e-f561-7a0a-97a4-11058661c03e:in_transit:{call_type}:{overnight_date}:{shipment_id}"
    else:
        cache_key = f"019b0e1e-f561-7a0a-97a4-11058661c03e:in_transit:{call_type}:{shipment_id}"

    cache_data = {
        "load_number": load_number,
        "call_type": call_type,
        "called_at": datetime.now(timezone.utc).isoformat()
    }

    if minutes_late is not None:
        cache_data["minutes_late"] = minutes_late

    ttl_seconds = REDIS_TTL_DAYS * 86400
    redis_client.set(cache_key, json.dumps(cache_data), ex=ttl_seconds)


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
    """Send webhook to HappyRobot"""
    if not MOTUS_IN_TRANSIT_WEBHOOK_URL:
        print("ERROR: MOTUS_IN_TRANSIT_WEBHOOK_URL not configured")
        return False

    try:
        response = requests.post(
            MOTUS_IN_TRANSIT_WEBHOOK_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Webhook failed: {e}")
        return False


def sync_in_transit() -> Dict[str, Any]:
    """
    Main in-transit sync logic with overnight-aware calling

    Business Hours (8 AM - 6 PM EST):
        Window 1 (checkin): 3-4 hours before delivery
        Window 2 (final): 0-30 minutes before delivery

    Overnight (6 PM - 8 AM EST):
        Monitor only, call ONLY if driver is 30+ minutes late

    For each shipment:
    1. Get full details from Turvo
    2. Check if overnight or business hours
    3. Apply appropriate call logic
    4. Build batch of calls (with call_type)
    5. Send single webhook to HappyRobot
    6. Mark each call type as completed

    Returns:
        dict: Summary of execution
    """
    # Check if we're in overnight mode
    is_overnight = turvo_utils.is_overnight_hours()
    mode = "OVERNIGHT" if is_overnight else "BUSINESS"

    print(f"SYNC START | {datetime.now(timezone.utc).isoformat()} | Mode: {mode}")

    # Step 1: Get ALL En Route shipments (status 2105) across all pages
    try:
        shipments = turvo_client.list_all_shipments(status=2105)
    except Exception as e:
        print(f"ERROR: Failed to get shipments: {e}")
        return {"success": False, "error": str(e), "calls_made": 0}

    if not shipments:
        print("SYNC COMPLETE | No shipments found")
        return {"success": True, "shipments_processed": 0, "calls_made": 0}

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

    if not shipments:
        print("SYNC COMPLETE | No valid shipments after filtering")
        return {"success": True, "shipments_processed": 0, "calls_made": 0}

    # Step 2: Process each shipment
    calls_to_make = []  # Single batch with all calls (checkin + final)
    owner_cache = {}  # In-memory cache for owner details during this sync

    # Counters for summary
    stats = {
        "checkin_already_called": 0,
        "checkin_triggered": 0,
        "checkin_outside_window": 0,
        "final_already_called": 0,
        "final_triggered": 0,
        "final_outside_window": 0,
        "late_check_already_called": 0,
        "late_check_triggered": 0,
        "late_check_not_late": 0,
        "owner_filtered": 0,
        "no_eta": 0,
        "missing_data": 0,
    }
    errors = []

    for i, shipment in enumerate(shipments, 1):
        shipment_id = shipment["id"]
        custom_id = shipment.get("customId", "Unknown")

        # Check which call types have already been made
        checkin_called = check_already_called(shipment_id, "checkin")
        final_called = check_already_called(shipment_id, "final")
        late_check_called = check_already_called(shipment_id, "late_check") if is_overnight else False

        # Skip if all applicable calls have been made
        if is_overnight:
            if late_check_called:
                stats["late_check_already_called"] += 1
                continue
        else:
            if checkin_called and final_called:
                stats["checkin_already_called"] += 1
                stats["final_already_called"] += 1
                continue

        # Get full details
        try:
            details = turvo_client.get_shipment_details(shipment_id)
        except Exception as e:
            errors.append({"load": custom_id, "error": str(e)})
            continue

        # Check owner filtering
        is_allowed, owner_info = check_owner_allowed(details)
        if not is_allowed:
            stats["owner_filtered"] += 1
            continue

        # Get owner contact info (with caching)
        owner_id = turvo_utils.extract_owner_id(details)
        owner_contact = None
        if owner_id:
            if owner_id not in owner_cache:
                try:
                    user_details = turvo_client.get_user_details(owner_id)
                    owner_cache[owner_id] = turvo_utils.extract_owner_contact_info(user_details)
                except Exception:
                    owner_cache[owner_id] = None
            owner_contact = owner_cache[owner_id]

        # Transform to webhook payload
        payload = turvo_utils.transform_shipment_for_webhook(details, owner_info=owner_contact)

        if not payload:
            # Missing critical data (logged by transform function)
            stats["missing_data"] += 1
            continue

        hours_until = payload["delivery"]["hours_until"]

        if hours_until is None:
            stats["no_eta"] += 1
            continue

        # Get GPS ETA and appointment for late check (needed for overnight logic)
        global_route = details.get("globalRoute", [])
        delivery_stop = turvo_utils.find_delivery_stop(global_route)
        gps_eta = delivery_stop.get("etaToStop", {}).get("etaValue") if delivery_stop else None
        appointment = delivery_stop.get("appointment", {}).get("date") if delivery_stop else None

        call_types_to_make = []
        minutes_late = None

        if is_overnight:
            # OVERNIGHT MODE: Only call if driver is 30+ minutes late
            if gps_eta and appointment:
                driver_is_late, minutes_late = turvo_utils.is_driver_late(gps_eta, appointment)
                if driver_is_late:
                    call_types_to_make.append("late_check")
                else:
                    stats["late_check_not_late"] += 1
            else:
                stats["late_check_not_late"] += 1
        else:
            # BUSINESS HOURS MODE: Normal window logic
            # Window 1: Check-in call (3-4 hours)
            if CALL_WINDOW_1_MIN <= hours_until <= CALL_WINDOW_1_MAX:
                if checkin_called:
                    stats["checkin_already_called"] += 1
                else:
                    call_types_to_make.append("checkin")
            else:
                stats["checkin_outside_window"] += 1

            # Window 2: Final call (0-30 min)
            if CALL_WINDOW_2_MIN <= hours_until <= CALL_WINDOW_2_MAX:
                if final_called:
                    stats["final_already_called"] += 1
                else:
                    call_types_to_make.append("final")
            else:
                stats["final_outside_window"] += 1

        # Add calls to batch
        for call_type in call_types_to_make:
            # Create payload with call_type
            call_payload = payload.copy()
            call_payload["call_type"] = call_type

            # For late_check, add how late the driver is
            if call_type == "late_check" and minutes_late:
                call_payload["minutes_late"] = minutes_late

            # Log calls that will be made
            if call_type == "late_check":
                print(f"  → LATE_CHECK call: {custom_id} | {payload['driver']['name']} | {minutes_late:.0f} min late | {payload['delivery']['location']['city']}, {payload['delivery']['location']['state']}")
            else:
                print(f"  → {call_type.upper()} call: {custom_id} | {payload['driver']['name']} | {payload['delivery']['location']['city']}, {payload['delivery']['location']['state']} | ETA: {payload['delivery']['eta_formatted']}")

            calls_to_make.append({
                "shipment_id": shipment_id,
                "load_number": custom_id,
                "call_type": call_type,
                "payload": call_payload,
                "minutes_late": minutes_late if call_type == "late_check" else None
            })

            if call_type == "checkin":
                stats["checkin_triggered"] += 1
            elif call_type == "final":
                stats["final_triggered"] += 1
            else:
                stats["late_check_triggered"] += 1

    # Step 3: Send all calls in one batch webhook
    if calls_to_make:
        # Sort calls: late_check first (urgent), then reefer loads, then by hours_until
        calls_to_make.sort(key=lambda c: (
            0 if c["call_type"] == "late_check" else 1,
            0 if c["payload"]["equipment"]["temperature"] is not None else 1,
            c["payload"]["delivery"]["hours_until"] or 999
        ))

        checkin_count = sum(1 for c in calls_to_make if c["call_type"] == "checkin")
        final_count = sum(1 for c in calls_to_make if c["call_type"] == "final")
        late_check_count = sum(1 for c in calls_to_make if c["call_type"] == "late_check")

        # Prepare batch payload
        batch_payload = {
            "shipments": [call["payload"] for call in calls_to_make],
            "total_calls": len(calls_to_make),
            "checkin_calls": checkin_count,
            "final_calls": final_count,
            "late_check_calls": late_check_count,
            "mode": mode,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # Send the batch
        if send_webhook(batch_payload):
            for call in calls_to_make:
                mark_as_called(
                    call["shipment_id"],
                    call["load_number"],
                    call["call_type"],
                    minutes_late=call.get("minutes_late")
                )
        else:
            errors.append({"error": "Batch webhook failed", "loads": [call["load_number"] for call in calls_to_make]})

    # Summary log
    if is_overnight:
        print(f"SYNC COMPLETE | Mode: {mode} | Processed: {len(shipments)} | Filtered: {stats['owner_filtered']} | Late Checks: {stats['late_check_triggered']} | On-Time: {stats['late_check_not_late']} | Errors: {len(errors)}")
    else:
        print(f"SYNC COMPLETE | Mode: {mode} | Processed: {len(shipments)} | Filtered: {stats['owner_filtered']} | Checkin: {stats['checkin_triggered']} | Final: {stats['final_triggered']} | Errors: {len(errors)}")

    return {
        "success": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "shipments_total": len(shipments),
        "shipments_processed": len(shipments),
        "owner_filtered": stats["owner_filtered"],
        "checkin_calls": stats["checkin_triggered"],
        "final_calls": stats["final_triggered"],
        "late_check_calls": stats["late_check_triggered"],
        "total_calls": len(calls_to_make),
        "errors": errors
    }
