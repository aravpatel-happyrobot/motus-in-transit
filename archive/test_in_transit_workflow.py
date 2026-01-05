"""
Test the complete in-transit workflow:
1. Get all En Route shipments
2. For each, fetch full details
3. Extract delivery ETA and driver phone
4. Calculate hours until delivery
5. Show which loads would trigger calls (≤ 4 hours)
"""

import os
import json
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

# Configuration
TURVO_BASE_URL = os.getenv("TURVO_BASE_URL", "https://publicapi.turvo.com/v1")
TURVO_API_KEY = os.getenv("TURVO_API_KEY")
TURVO_USERNAME = os.getenv("TURVO_USERNAME")
TURVO_PASSWORD = os.getenv("TURVO_PASSWORD")

# Colors for output
class c:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'

def get_token():
    """Get OAuth token"""
    print(f"{c.BLUE}→ Authenticating...{c.END}")

    url = f"{TURVO_BASE_URL}/oauth/token"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": TURVO_API_KEY
    }
    payload = {
        "grant_type": "password",
        "username": TURVO_USERNAME,
        "password": TURVO_PASSWORD,
        "client_id": "publicapi",
        "client_secret": "secret",
        "scope": "read+trust+write",
        "type": "business"
    }

    response = requests.post(url, headers=headers, json=payload)
    token = response.json()["access_token"]
    print(f"{c.GREEN}✓ Got access token{c.END}\n")
    return token

def turvo_get(token, endpoint, params=None):
    """Make GET request to Turvo API"""
    url = f"{TURVO_BASE_URL}{endpoint}"
    headers = {
        "Authorization": f"Bearer {token}",
        "x-api-key": TURVO_API_KEY,
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        print(f"{c.RED}✗ API Error: {response.status_code} - {response.text[:200]}{c.END}")
        return None

    return response.json()

def find_delivery_stop(global_route):
    """Find the delivery stop from globalRoute"""
    if not global_route:
        return None

    for stop in global_route:
        stop_type = stop.get("stopType", {}).get("value")
        state = stop.get("state")

        if stop_type == "Delivery" and state == "OPEN":
            return stop

    return None

def extract_driver_phone(shipment_details):
    """Extract driver phone number from shipment details"""
    carrier_orders = shipment_details.get("carrierOrder", [])

    for carrier_order in carrier_orders:
        if carrier_order.get("deleted"):
            continue

        drivers = carrier_order.get("drivers", [])
        for driver in drivers:
            context = driver.get("context", {})
            phones = context.get("phones", [])

            if phones:
                return phones[0].get("number")

    return None

def calculate_hours_until(eta_iso):
    """Calculate hours until delivery from ISO timestamp"""
    try:
        eta_dt = datetime.fromisoformat(eta_iso.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        hours = (eta_dt - now).total_seconds() / 3600
        return round(hours, 1)
    except:
        return None

def test_workflow():
    """Test the complete in-transit workflow"""

    print(f"{c.BOLD}{'='*80}{c.END}")
    print(f"{c.BOLD}IN-TRANSIT WORKFLOW TEST{c.END}")
    print(f"{c.BOLD}{'='*80}{c.END}\n")

    # Step 1: Authenticate
    token = get_token()

    # Step 2: Get all En Route shipments
    print(f"{c.BLUE}→ Querying En Route shipments (status 2105)...{c.END}")
    list_response = turvo_get(token, "/shipments/list", params={
        "status[eq]": 2105,
        "pageSize": 50
    })

    if not list_response:
        print(f"{c.RED}✗ Failed to get shipments list{c.END}")
        return

    shipments = list_response.get("details", {}).get("shipments", [])
    print(f"{c.GREEN}✓ Found {len(shipments)} En Route shipments{c.END}\n")

    if not shipments:
        print(f"{c.YELLOW}No En Route shipments found. Test complete.{c.END}")
        return

    # Step 3: Process each shipment
    print(f"{c.BOLD}{'='*80}{c.END}")
    print(f"{c.BOLD}PROCESSING SHIPMENTS{c.END}")
    print(f"{c.BOLD}{'='*80}{c.END}\n")

    results = []

    for i, shipment in enumerate(shipments[:10], 1):  # Limit to 10 for testing
        shipment_id = shipment["id"]
        custom_id = shipment["customId"]

        print(f"{c.BLUE}[{i}/{min(len(shipments), 10)}] Load {custom_id} (ID: {shipment_id}){c.END}")

        # Get full details
        details = turvo_get(token, f"/shipments/{shipment_id}")

        if not details or "details" not in details:
            print(f"  {c.RED}✗ Failed to get shipment details{c.END}\n")
            continue

        shipment_data = details["details"]

        # Find delivery stop
        global_route = shipment_data.get("globalRoute", [])
        delivery_stop = find_delivery_stop(global_route)

        if not delivery_stop:
            print(f"  {c.YELLOW}⚠ No open delivery stop found{c.END}\n")
            continue

        # Get ETA
        eta_to_stop = delivery_stop.get("etaToStop", {})
        eta_value = eta_to_stop.get("etaValue")
        eta_formatted = eta_to_stop.get("formattedEtaValue")
        miles_remaining = eta_to_stop.get("nextStopMiles")

        if not eta_value:
            print(f"  {c.YELLOW}⚠ No ETA available{c.END}\n")
            continue

        # Calculate hours until delivery
        hours_until = calculate_hours_until(eta_value)

        # Get delivery location
        delivery_city = delivery_stop.get("address", {}).get("city", "Unknown")
        delivery_state = delivery_stop.get("address", {}).get("state", "")

        # Get driver phone
        driver_phone = extract_driver_phone(shipment_data)

        # Determine if we should call
        should_call = hours_until is not None and hours_until <= 4

        result = {
            "custom_id": custom_id,
            "shipment_id": shipment_id,
            "hours_until_delivery": hours_until,
            "eta_formatted": eta_formatted,
            "miles_remaining": miles_remaining,
            "delivery_location": f"{delivery_city}, {delivery_state}",
            "driver_phone": driver_phone,
            "should_call": should_call
        }
        results.append(result)

        # Print details
        print(f"  Delivering to: {c.BOLD}{delivery_city}, {delivery_state}{c.END}")
        print(f"  ETA: {eta_formatted} ({eta_value})")
        print(f"  Hours until delivery: {c.BOLD}{hours_until}h{c.END}")
        print(f"  Miles remaining: {miles_remaining}")
        print(f"  Driver phone: {driver_phone or 'Not available'}")

        if should_call:
            print(f"  {c.GREEN}{c.BOLD}✓ WOULD TRIGGER CALL (≤ 4 hours){c.END}")
        else:
            print(f"  {c.YELLOW}○ No call needed (> 4 hours){c.END}")

        print()

    # Summary
    print(f"{c.BOLD}{'='*80}{c.END}")
    print(f"{c.BOLD}SUMMARY{c.END}")
    print(f"{c.BOLD}{'='*80}{c.END}\n")

    total_processed = len(results)
    calls_needed = sum(1 for r in results if r["should_call"])
    no_eta = len([s for s in shipments[:10] if s not in [r["shipment_id"] for r in results]])

    print(f"Total shipments processed: {total_processed}")
    print(f"Shipments without ETA/delivery: {no_eta}")
    print(f"{c.GREEN}{c.BOLD}Calls that would be triggered: {calls_needed}{c.END}\n")

    if calls_needed > 0:
        print(f"{c.BOLD}Loads requiring calls:{c.END}")
        for result in results:
            if result["should_call"]:
                print(f"  • {c.GREEN}{result['custom_id']}{c.END} - "
                      f"{result['hours_until_delivery']}h until delivery to {result['delivery_location']}")
                print(f"    Phone: {result['driver_phone'] or 'N/A'}")
        print()

    # Save results
    os.makedirs("turvo_test_responses", exist_ok=True)
    with open("turvo_test_responses/in_transit_workflow_results.json", "w") as f:
        json.dump({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_en_route": len(shipments),
            "processed": total_processed,
            "calls_needed": calls_needed,
            "results": results
        }, f, indent=2)

    print(f"{c.BLUE}Results saved to: turvo_test_responses/in_transit_workflow_results.json{c.END}")

    # Final verdict
    print(f"\n{c.BOLD}{'='*80}{c.END}")
    if calls_needed > 0:
        print(f"{c.GREEN}{c.BOLD}✓ WORKFLOW WORKS! Found {calls_needed} load(s) ready for in-transit calls.{c.END}")
    else:
        print(f"{c.YELLOW}○ Workflow works, but no loads currently within 4 hours of delivery.{c.END}")
    print(f"{c.BOLD}{'='*80}{c.END}\n")

if __name__ == "__main__":
    test_workflow()
