"""
Turvo data transformation utilities

Extracts and transforms data from Turvo API responses into
standardized format for HappyRobot webhooks
"""

import re
from datetime import datetime, timezone
from typing import Optional, Dict, Any


def find_delivery_stop(global_route: list) -> Optional[Dict[str, Any]]:
    """
    Find the open delivery stop from globalRoute

    Args:
        global_route: Array of stop objects

    Returns:
        dict: Delivery stop object or None if not found
    """
    if not global_route:
        return None

    for stop in global_route:
        stop_type = stop.get("stopType", {}).get("value")
        state = stop.get("state")

        if stop_type == "Delivery" and state == "OPEN":
            return stop

    return None


def find_pickup_stop(global_route: list) -> Optional[Dict[str, Any]]:
    """
    Find the pickup stop from globalRoute

    Args:
        global_route: Array of stop objects

    Returns:
        dict: Pickup stop object or None if not found
    """
    if not global_route:
        return None

    for stop in global_route:
        stop_type = stop.get("stopType", {}).get("value")

        if stop_type == "Pickup":
            return stop

    return None


def calculate_hours_until(eta_iso: str) -> Optional[float]:
    """
    Calculate hours until delivery from ISO timestamp

    Args:
        eta_iso: ISO 8601 timestamp (e.g., "2026-01-05T07:37:53Z")

    Returns:
        float: Hours until delivery (rounded to 1 decimal) or None if invalid
    """
    try:
        eta_dt = datetime.fromisoformat(eta_iso.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        hours = (eta_dt - now).total_seconds() / 3600
        return round(hours, 1)
    except (ValueError, AttributeError):
        return None


def clean_driver_name(name: Optional[str]) -> Optional[str]:
    """
    Clean and format driver name for AI calls

    Removes numbers, special characters, gets first name only, and title cases

    Args:
        name: Raw driver name from TMS

    Returns:
        str: Cleaned first name (e.g., "Juan Carlos 123" -> "Juan")
    """
    if not name:
        return None

    # Remove numbers and special characters (keep letters and spaces)
    cleaned = re.sub(r'[^a-zA-Z ]', '', name)

    # Get first name only and title case
    parts = cleaned.split()
    if parts:
        return parts[0].title()

    return None


def extract_driver_info(shipment: Dict[str, Any]) -> Dict[str, Optional[str]]:
    """
    Extract driver name and phone from shipment

    Takes the LAST driver in the list (most recent assignment)

    Args:
        shipment: Full shipment object

    Returns:
        dict: {"name": str, "phone": str} or both None if not found
    """
    carrier_orders = shipment.get("carrierOrder", [])

    for carrier_order in carrier_orders:
        # Skip deleted carrier assignments
        if carrier_order.get("deleted"):
            continue

        drivers = carrier_order.get("drivers", [])
        if not drivers:
            continue

        # Take the LAST driver (most recent)
        driver = drivers[-1]
        context = driver.get("context", {})

        driver_name = context.get("name")
        # Clean the driver name for AI calls
        driver_name = clean_driver_name(driver_name)

        phones = context.get("phones", [])
        driver_phone = phones[0].get("number") if phones else None

        if driver_phone:  # At least need phone number
            return {
                "name": driver_name,
                "phone": driver_phone
            }

    return {"name": None, "phone": None}


def extract_equipment_info(shipment: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract equipment information including temperature for reefers

    Always includes temperature fields (null for non-reefers)

    Args:
        shipment: Full shipment object

    Returns:
        dict: Equipment data with type, size, temperature, etc.
    """
    equipment = shipment.get("equipment", [])

    if not equipment:
        return {
            "type": None,
            "size": None,
            "temperature": None,
            "temp_units": None,
            "weight": None,
            "weight_units": None,
            "description": None
        }

    equip = equipment[0]

    # Helper to safely get nested values
    def safe_get(obj, key):
        val = obj.get(key)
        if isinstance(val, dict):
            return val.get("value")
        return val

    return {
        "type": safe_get(equip, "type"),
        "size": safe_get(equip, "size"),
        "temperature": equip.get("temp"),  # Will be None for non-reefers
        "temp_units": safe_get(equip, "tempUnits") if "temp" in equip else None,
        "weight": equip.get("weight"),
        "weight_units": safe_get(equip, "weightUnits"),
        "description": equip.get("description")
    }


def extract_notes(shipment: Dict[str, Any]) -> Dict[str, Optional[str]]:
    """
    Extract notes from various locations in shipment

    Args:
        shipment: Full shipment object

    Returns:
        dict: Notes from status, pickup, delivery, equipment
    """
    global_route = shipment.get("globalRoute", [])

    pickup_stop = find_pickup_stop(global_route)
    delivery_stop = find_delivery_stop(global_route)

    equipment = shipment.get("equipment", [])

    return {
        "status": shipment.get("status", {}).get("notes"),
        "pickup": pickup_stop.get("notes") if pickup_stop else None,
        "delivery": delivery_stop.get("notes") if delivery_stop else None,
        "equipment": equipment[0].get("description") if equipment else None
    }


def extract_location_info(stop: Optional[Dict[str, Any]]) -> Dict[str, Optional[str]]:
    """
    Extract location information from a stop

    Args:
        stop: Stop object from globalRoute

    Returns:
        dict: Location data with name, city, state, address
    """
    if not stop:
        return {
            "name": None,
            "city": None,
            "state": None,
            "address": None
        }

    address = stop.get("address", {})

    return {
        "name": stop.get("name"),
        "city": address.get("city"),
        "state": address.get("state"),
        "address": address.get("line1")
    }


def extract_carrier_info(shipment: Dict[str, Any]) -> Dict[str, Optional[Any]]:
    """
    Extract carrier information

    Args:
        shipment: Full shipment object

    Returns:
        dict: Carrier name and ID
    """
    carrier_orders = shipment.get("carrierOrder", [])

    for carrier_order in carrier_orders:
        if carrier_order.get("deleted"):
            continue

        carrier = carrier_order.get("carrier", {})
        return {
            "name": carrier.get("name"),
            "id": carrier.get("id")
        }

    return {"name": None, "id": None}


def extract_customer_info(shipment: Dict[str, Any]) -> Dict[str, Optional[Any]]:
    """
    Extract customer information

    Args:
        shipment: Full shipment object

    Returns:
        dict: Customer name and ID
    """
    customer_orders = shipment.get("customerOrder", [])

    if not customer_orders:
        return {"name": None, "id": None}

    customer = customer_orders[0].get("customer", {})
    return {
        "name": customer.get("name"),
        "id": customer.get("id")
    }


def extract_owner_id(shipment: Dict[str, Any]) -> Optional[int]:
    """
    Extract owner ID from shipment

    Args:
        shipment: Full shipment object

    Returns:
        int: Owner ID or None
    """
    customer_orders = shipment.get("customerOrder", [])

    for co in customer_orders:
        if co.get("deleted"):
            continue
        customer = co.get("customer", {})
        owner = customer.get("owner", {})
        owner_id = owner.get("id")
        if owner_id:
            return owner_id

    return None


def extract_owner_contact_info(user_details: Dict[str, Any]) -> Dict[str, Optional[str]]:
    """
    Extract owner contact info from user details

    Args:
        user_details: User object from /users/{id} endpoint

    Returns:
        dict: Owner name, email, phone
    """
    if not user_details:
        return {"name": None, "id": None, "email": None, "phone": None}

    # Get primary email
    emails = user_details.get("email", [])
    primary_email = next((e["email"] for e in emails if e.get("isPrimary")), None)

    # Get primary phone
    phones = user_details.get("phone", [])
    primary_phone = next((p["number"] for p in phones if p.get("isPrimary")), None)

    return {
        "name": user_details.get("name"),
        "id": user_details.get("id"),
        "email": primary_email,
        "phone": primary_phone
    }


def transform_shipment_for_webhook(shipment: Dict[str, Any], owner_info: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    Transform Turvo shipment into HappyRobot webhook payload

    Args:
        shipment: Full Turvo shipment object
        owner_info: Optional owner contact info (name, email, phone)

    Returns:
        dict: Webhook payload or None if missing critical data
    """
    # Extract basic info
    load_number = shipment.get("customId")
    shipment_id = shipment.get("id")

    # Get route info
    global_route = shipment.get("globalRoute", [])
    pickup_stop = find_pickup_stop(global_route)
    delivery_stop = find_delivery_stop(global_route)

    if not delivery_stop:
        print(f"⚠ Shipment {load_number}: No open delivery stop")
        return None

    # Get ETA
    eta_to_stop = delivery_stop.get("etaToStop", {})
    eta_value = eta_to_stop.get("etaValue")
    eta_formatted = eta_to_stop.get("formattedEtaValue")
    miles_remaining = eta_to_stop.get("nextStopMiles")

    if not eta_value:
        print(f"⚠ Shipment {load_number}: No ETA available")
        return None

    hours_until = calculate_hours_until(eta_value)

    # Get driver info
    driver = extract_driver_info(shipment)
    if not driver["phone"]:
        print(f"⚠ Shipment {load_number}: No driver phone number")
        return None

    # Build payload
    payload = {
        "load_number": load_number,
        "shipment_id": shipment_id,

        "driver": {
            "name": driver["name"],
            "phone": driver["phone"]
        },

        "delivery": {
            "eta": eta_value,
            "eta_formatted": eta_formatted,
            "hours_until": hours_until,
            "miles_remaining": miles_remaining,
            "location": extract_location_info(delivery_stop)
        },

        "pickup": {
            "location": extract_location_info(pickup_stop)
        },

        "equipment": extract_equipment_info(shipment),

        "notes": extract_notes(shipment),

        "carrier": extract_carrier_info(shipment),

        "customer": extract_customer_info(shipment),

        "owner": owner_info or {"name": None, "id": None, "email": None, "phone": None},

        "source": "motus_in_transit",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    return payload
