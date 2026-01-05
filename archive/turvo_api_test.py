"""
Turvo API Test Script for Motus Freight Integration

This script tests the Turvo API to verify:
1. Authentication (OAuth2) works
2. Shipment listing with various filters
3. Data structure and field availability
4. Driver contact information
5. ETA and distance data

Usage:
    python turvo_api_test.py

Requirements:
    pip install requests python-dotenv
"""

import os
import json
import requests
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Turvo API Configuration
TURVO_BASE_URL = os.getenv("TURVO_BASE_URL", "https://publicapi.turvo.com/v1")
TURVO_API_KEY = os.getenv("TURVO_API_KEY", "9CtJ7rMImv6BTB6x922xR6xDN6ckpiTG4FKrvbL1")
TURVO_USERNAME = os.getenv("TURVO_USERNAME", "support@happyrobot.ai")
TURVO_PASSWORD = os.getenv("TURVO_PASSWORD", "")  # SET THIS IN .env
TURVO_CLIENT_ID = os.getenv("TURVO_CLIENT_ID", "publicapi")
TURVO_CLIENT_SECRET = os.getenv("TURVO_CLIENT_SECRET", "secret")

# Global token storage
access_token = None
token_expires_at = None


class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_section(title: str):
    """Print a formatted section header"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{title}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}\n")


def print_success(message: str):
    """Print success message"""
    print(f"{Colors.OKGREEN}✓ {message}{Colors.ENDC}")


def print_error(message: str):
    """Print error message"""
    print(f"{Colors.FAIL}✗ {message}{Colors.ENDC}")


def print_warning(message: str):
    """Print warning message"""
    print(f"{Colors.WARNING}⚠ {message}{Colors.ENDC}")


def print_info(message: str):
    """Print info message"""
    print(f"{Colors.OKCYAN}ℹ {message}{Colors.ENDC}")


def save_response(filename: str, data: dict):
    """Save API response to file for analysis"""
    output_dir = "turvo_test_responses"
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename)

    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)

    print_info(f"Response saved to: {filepath}")


def get_access_token() -> Optional[str]:
    """
    Authenticate with Turvo API using OAuth2 password grant

    Returns:
        Access token string or None if authentication fails
    """
    global access_token, token_expires_at

    # Check if we have a valid cached token
    if access_token and token_expires_at:
        if datetime.now() < token_expires_at:
            print_info("Using cached access token")
            return access_token

    print_section("TEST 1: OAuth2 Authentication")

    if not TURVO_PASSWORD:
        print_error("TURVO_PASSWORD not set in environment variables!")
        print_warning("Please add TURVO_PASSWORD to your .env file")
        return None

    url = f"{TURVO_BASE_URL}/oauth/token"

    headers = {
        "Content-Type": "application/json",
        "x-api-key": TURVO_API_KEY
    }

    payload = {
        "grant_type": "password",
        "username": TURVO_USERNAME,
        "password": TURVO_PASSWORD,
        "client_id": TURVO_CLIENT_ID,
        "client_secret": TURVO_CLIENT_SECRET,
        "scope": "read+trust+write",
        "type": "business"
    }

    print_info(f"POST {url}")
    print_info(f"Username: {TURVO_USERNAME}")
    print_info(f"API Key: {TURVO_API_KEY[:20]}...")

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)

        print_info(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            access_token = data.get("access_token")
            expires_in = data.get("expires_in", 3600)  # Default 1 hour

            # Cache token expiration (with 5 min buffer)
            token_expires_at = datetime.now() + timedelta(seconds=expires_in - 300)

            print_success("Authentication successful!")
            print_info(f"Token expires in: {expires_in} seconds ({expires_in/3600:.1f} hours)")
            print_info(f"Token: {access_token[:30]}...")

            save_response("auth_response.json", data)

            return access_token
        else:
            print_error(f"Authentication failed: {response.status_code}")
            print_error(f"Response: {response.text}")
            save_response("auth_error.json", {
                "status_code": response.status_code,
                "response": response.text
            })
            return None

    except requests.exceptions.RequestException as e:
        print_error(f"Request failed: {str(e)}")
        return None


def list_shipments(params: Dict, test_name: str) -> Optional[List[Dict]]:
    """
    Query Turvo shipments API with given parameters

    Args:
        params: Query parameters for filtering
        test_name: Name of this test for logging

    Returns:
        List of shipment dictionaries or None if failed
    """
    token = get_access_token()
    if not token:
        return None

    url = f"{TURVO_BASE_URL}/shipments/list"

    headers = {
        "Authorization": f"Bearer {token}",
        "x-api-key": TURVO_API_KEY,
        "Content-Type": "application/json"
    }

    print_info(f"GET {url}")
    print_info(f"Params: {params}")

    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)

        print_info(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()

            # Extract shipments from response
            shipments = data.get("details", {}).get("Shipments", [])

            print_success(f"Query successful! Found {len(shipments)} shipments")

            # Save full response
            save_response(f"{test_name}_response.json", data)

            return shipments
        else:
            print_error(f"Query failed: {response.status_code}")
            print_error(f"Response: {response.text}")
            save_response(f"{test_name}_error.json", {
                "status_code": response.status_code,
                "response": response.text
            })
            return None

    except requests.exceptions.RequestException as e:
        print_error(f"Request failed: {str(e)}")
        return None


def analyze_shipment_structure(shipments: List[Dict]):
    """
    Analyze shipment data structure to verify required fields

    Args:
        shipments: List of shipment dictionaries
    """
    print_section("DATA STRUCTURE ANALYSIS")

    if not shipments:
        print_warning("No shipments to analyze")
        return

    print_info(f"Analyzing {len(shipments)} shipments...")

    # Take first shipment as sample
    sample = shipments[0]

    print("\n" + Colors.BOLD + "Sample Shipment Keys:" + Colors.ENDC)
    for key in sample.keys():
        print(f"  - {key}")

    # Check critical fields
    print("\n" + Colors.BOLD + "Critical Field Availability:" + Colors.ENDC)

    checks = [
        ("Shipment ID", ["id"]),
        ("Custom ID (Load Number)", ["customId"]),
        ("Status Code", ["status", "code", "value"]),
        ("Status Description", ["status", "description"]),
        ("Global Route (Stops)", ["globalRoute"]),
        ("Carrier Order", ["carrierOrder"]),
    ]

    for field_name, path in checks:
        value = sample
        try:
            for key in path:
                if isinstance(value, list) and len(value) > 0:
                    value = value[0]
                value = value[key]
            print_success(f"{field_name}: Available")
            print_info(f"  Value: {value if not isinstance(value, (dict, list)) else type(value).__name__}")
        except (KeyError, IndexError, TypeError):
            print_error(f"{field_name}: NOT FOUND")

    # Analyze stops/route
    if "globalRoute" in sample and sample["globalRoute"]:
        print("\n" + Colors.BOLD + "Route/Stop Analysis:" + Colors.ENDC)
        route = sample["globalRoute"]
        print_info(f"Number of stops: {len(route)}")

        for i, stop in enumerate(route):
            stop_type = stop.get("stopType", {}).get("value", "Unknown")
            stop_state = stop.get("state", "Unknown")
            city = stop.get("address", {}).get("city", "Unknown")

            # Check ETA data
            eta_to_stop = stop.get("etaToStop", {})
            eta_value = eta_to_stop.get("etaValue")
            next_stop_miles = eta_to_stop.get("nextStopMiles")

            print(f"\n  Stop {i+1}: {stop_type} - {city}")
            print(f"    State: {stop_state}")

            if eta_value:
                print_success(f"    ETA: {eta_value}")
            else:
                print_warning(f"    ETA: Not available")

            if next_stop_miles is not None:
                print_success(f"    Miles Remaining: {next_stop_miles}")
            else:
                print_warning(f"    Miles Remaining: Not available")

    # Analyze driver info
    if "carrierOrder" in sample and sample["carrierOrder"]:
        print("\n" + Colors.BOLD + "Driver/Carrier Info:" + Colors.ENDC)
        carrier_order = sample["carrierOrder"][0]

        carrier_name = carrier_order.get("carrier", {}).get("name", "Unknown")
        print_info(f"Carrier: {carrier_name}")

        if "drivers" in carrier_order and carrier_order["drivers"]:
            driver = carrier_order["drivers"][0]
            driver_name = driver.get("context", {}).get("name", "Unknown")
            driver_phone = driver.get("phone", {}).get("number")

            print_info(f"Driver: {driver_name}")

            if driver_phone:
                print_success(f"Driver Phone: {driver_phone}")
            else:
                print_error("Driver Phone: NOT FOUND")
        else:
            print_warning("No driver information available")

    # Save detailed analysis
    analysis = {
        "total_shipments": len(shipments),
        "sample_shipment_id": sample.get("id"),
        "sample_custom_id": sample.get("customId"),
        "available_fields": list(sample.keys()),
        "route_stops": len(sample.get("globalRoute", [])),
    }
    save_response("structure_analysis.json", analysis)


def test_en_route_shipments():
    """Test: Query shipments with En Route status"""
    print_section("TEST 2: En Route Shipments")

    params = {
        "status[eq]": 2105,  # En Route
        "pageSize": 10
    }

    shipments = list_shipments(params, "en_route_shipments")

    if shipments:
        analyze_shipment_structure(shipments)

    return shipments


def test_delivery_date_filter():
    """Test: Filter by delivery date range"""
    print_section("TEST 3: Delivery Date Filtering")

    now = datetime.now(timezone.utc)
    tomorrow = now + timedelta(days=1)

    params = {
        "status[eq]": 2105,  # En Route
        "deliveryDate[gte]": now.isoformat(),
        "deliveryDate[lte]": tomorrow.isoformat(),
        "pageSize": 50
    }

    print_info(f"Querying deliveries from {now.strftime('%Y-%m-%d %H:%M')} to {tomorrow.strftime('%Y-%m-%d %H:%M')} UTC")

    shipments = list_shipments(params, "delivery_date_filter")

    if shipments:
        print_success(f"Found {len(shipments)} shipments delivering in next 24 hours")

        # Analyze delivery times
        print("\n" + Colors.BOLD + "Delivery Time Distribution:" + Colors.ENDC)
        for shipment in shipments[:5]:  # Show first 5
            custom_id = shipment.get("customId", "N/A")
            route = shipment.get("globalRoute", [])

            # Find delivery stop
            delivery_stop = None
            for stop in route:
                if stop.get("stopType", {}).get("value") == "Delivery":
                    delivery_stop = stop
                    break

            if delivery_stop:
                eta = delivery_stop.get("etaToStop", {}).get("etaValue")
                if eta:
                    eta_dt = datetime.fromisoformat(eta.replace("Z", "+00:00"))
                    hours_from_now = (eta_dt - now).total_seconds() / 3600
                    print(f"  Load {custom_id}: Delivers in {hours_from_now:.1f} hours ({eta})")
                else:
                    print(f"  Load {custom_id}: No ETA available")

    return shipments


def test_pre_delivery_window():
    """Test: Find shipments that need calls 3 hours before delivery"""
    print_section("TEST 4: Pre-Delivery Call Window (3 hours before)")

    # Query shipments delivering in next 24 hours
    now = datetime.now(timezone.utc)
    tomorrow = now + timedelta(days=1)

    params = {
        "status[eq]": 2105,
        "deliveryDate[gte]": now.isoformat(),
        "deliveryDate[lte]": tomorrow.isoformat(),
        "pageSize": 50
    }

    shipments = list_shipments(params, "pre_delivery_window")

    if not shipments:
        return None

    # Filter for shipments in the 2.5-3.5 hour window
    CALL_HOURS_BEFORE = 3
    WINDOW_BUFFER = 0.5

    calls_needed = []

    print("\n" + Colors.BOLD + "Analyzing call windows:" + Colors.ENDC)

    for shipment in shipments:
        custom_id = shipment.get("customId", "N/A")
        route = shipment.get("globalRoute", [])

        # Find delivery stop
        delivery_stop = None
        for stop in route:
            if stop.get("stopType", {}).get("value") == "Delivery" and stop.get("state") == "OPEN":
                delivery_stop = stop
                break

        if not delivery_stop:
            continue

        eta = delivery_stop.get("etaToStop", {}).get("etaValue")
        if not eta:
            continue

        # Calculate hours until delivery
        eta_dt = datetime.fromisoformat(eta.replace("Z", "+00:00"))
        hours_until = (eta_dt - now).total_seconds() / 3600

        # Check if in call window
        min_hours = CALL_HOURS_BEFORE - WINDOW_BUFFER
        max_hours = CALL_HOURS_BEFORE + WINDOW_BUFFER

        if min_hours <= hours_until <= max_hours:
            miles = delivery_stop.get("etaToStop", {}).get("nextStopMiles")
            calls_needed.append({
                "customId": custom_id,
                "hoursUntilDelivery": round(hours_until, 1),
                "milesRemaining": miles,
                "eta": eta
            })
            print_success(f"  ✓ Load {custom_id}: {hours_until:.1f}h until delivery, {miles} miles - CALL NOW")
        else:
            status = "too early" if hours_until > max_hours else "too late"
            print_info(f"  - Load {custom_id}: {hours_until:.1f}h until delivery - {status}")

    print(f"\n{Colors.BOLD}Summary:{Colors.ENDC}")
    print_success(f"Total shipments in call window (2.5-3.5h): {len(calls_needed)}")

    if calls_needed:
        save_response("calls_needed_now.json", calls_needed)

    return calls_needed


def test_in_transit_identification():
    """Test: Identify shipments that are truly in transit (picked up but not delivered)"""
    print_section("TEST 5: In-Transit Identification")

    params = {
        "status[eq]": 2105,  # En Route
        "pageSize": 50
    }

    shipments = list_shipments(params, "in_transit_identification")

    if not shipments:
        return None

    in_transit = []

    print("\n" + Colors.BOLD + "Analyzing transit status:" + Colors.ENDC)

    for shipment in shipments:
        custom_id = shipment.get("customId", "N/A")
        route = shipment.get("globalRoute", [])

        if not route:
            continue

        # Check first stop (should be completed = picked up)
        first_stop = route[0]
        first_stop_state = first_stop.get("state")

        # Check last stop (should be open = not delivered)
        last_stop = route[-1]
        last_stop_state = last_stop.get("state")

        is_picked_up = first_stop_state == "COMPLETED"
        is_not_delivered = last_stop_state == "OPEN"

        if is_picked_up and is_not_delivered:
            in_transit.append(custom_id)
            print_success(f"  ✓ Load {custom_id}: Picked up, in transit")
        else:
            reason = []
            if not is_picked_up:
                reason.append("not picked up yet")
            if not is_not_delivered:
                reason.append("already delivered")
            print_info(f"  - Load {custom_id}: {', '.join(reason)}")

    print(f"\n{Colors.BOLD}Summary:{Colors.ENDC}")
    print_success(f"Shipments truly in transit: {len(in_transit)}")

    return in_transit


def run_all_tests():
    """Run all Turvo API tests"""
    print(f"{Colors.HEADER}{Colors.BOLD}")
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║                   TURVO API TEST SUITE - MOTUS FREIGHT                       ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    print(Colors.ENDC)

    # Test 1: Authentication
    token = get_access_token()
    if not token:
        print_error("\nAuthentication failed. Cannot proceed with tests.")
        print_warning("Please check your credentials in .env file")
        return

    # Test 2: En Route Shipments
    en_route = test_en_route_shipments()

    # Test 3: Delivery Date Filtering
    delivery_filtered = test_delivery_date_filter()

    # Test 4: Pre-Delivery Call Window
    calls_needed = test_pre_delivery_window()

    # Test 5: In-Transit Identification
    in_transit = test_in_transit_identification()

    # Final Summary
    print_section("FINAL SUMMARY")

    results = [
        ("Authentication", token is not None),
        ("En Route Shipments Query", en_route is not None),
        ("Delivery Date Filtering", delivery_filtered is not None),
        ("Pre-Delivery Call Logic", calls_needed is not None),
        ("In-Transit Identification", in_transit is not None),
    ]

    for test_name, passed in results:
        if passed:
            print_success(f"{test_name}: PASSED")
        else:
            print_error(f"{test_name}: FAILED")

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    print(f"\n{Colors.BOLD}Overall: {passed_count}/{total_count} tests passed{Colors.ENDC}")

    if passed_count == total_count:
        print_success("\n🎉 All tests passed! Ready to proceed with implementation.")
    elif passed_count > 0:
        print_warning(f"\n⚠️  {total_count - passed_count} test(s) failed. Review errors above.")
    else:
        print_error("\n❌ All tests failed. Check authentication and API access.")

    print_info("\nTest responses saved to: ./turvo_test_responses/")


if __name__ == "__main__":
    run_all_tests()
