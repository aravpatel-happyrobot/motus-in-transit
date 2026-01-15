"""
Turvo data transformation utilities

Extracts and transforms data from Turvo API responses into
standardized format for HappyRobot webhooks
"""

import re
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple
from zoneinfo import ZoneInfo


# Timezone for overnight hours check (Motus office is EST)
EST_TIMEZONE = ZoneInfo("America/New_York")

# Overnight hours in EST (6 PM to 8 AM)
OVERNIGHT_START_HOUR = 18  # 6 PM EST
OVERNIGHT_END_HOUR = 8     # 8 AM EST

# Late threshold in minutes
LATE_THRESHOLD_MINUTES = 30


# US State to Timezone mapping (primary timezone for each state)
STATE_TO_TIMEZONE = {
    # Eastern Time
    "CT": "America/New_York", "DE": "America/New_York", "DC": "America/New_York",
    "FL": "America/New_York", "GA": "America/New_York", "IN": "America/New_York",
    "KY": "America/New_York", "ME": "America/New_York", "MD": "America/New_York",
    "MA": "America/New_York", "MI": "America/New_York", "NH": "America/New_York",
    "NJ": "America/New_York", "NY": "America/New_York", "NC": "America/New_York",
    "OH": "America/New_York", "PA": "America/New_York", "RI": "America/New_York",
    "SC": "America/New_York", "VT": "America/New_York", "VA": "America/New_York",
    "WV": "America/New_York",
    # Central Time
    "AL": "America/Chicago", "AR": "America/Chicago", "IL": "America/Chicago",
    "IA": "America/Chicago", "KS": "America/Chicago", "LA": "America/Chicago",
    "MN": "America/Chicago", "MS": "America/Chicago", "MO": "America/Chicago",
    "NE": "America/Chicago", "ND": "America/Chicago", "OK": "America/Chicago",
    "SD": "America/Chicago", "TN": "America/Chicago", "TX": "America/Chicago",
    "WI": "America/Chicago",
    # Mountain Time
    "AZ": "America/Phoenix",  # No DST
    "CO": "America/Denver", "ID": "America/Denver", "MT": "America/Denver",
    "NM": "America/Denver", "UT": "America/Denver", "WY": "America/Denver",
    # Pacific Time
    "CA": "America/Los_Angeles", "NV": "America/Los_Angeles",
    "OR": "America/Los_Angeles", "WA": "America/Los_Angeles",
    # Alaska & Hawaii
    "AK": "America/Anchorage", "HI": "Pacific/Honolulu",
}


def is_overnight_hours() -> bool:
    """
    Check if current time is overnight hours (6 PM - 8 AM EST)

    Overnight = Motus office is closed, use monitoring-only logic

    Returns:
        bool: True if currently overnight (6 PM - 8 AM EST)
    """
    now_est = datetime.now(EST_TIMEZONE)
    hour = now_est.hour

    # Overnight is 6 PM (18:00) to 8 AM (08:00)
    # This means: hour >= 18 OR hour < 8
    return hour >= OVERNIGHT_START_HOUR or hour < OVERNIGHT_END_HOUR


def is_driver_late(gps_eta_iso: str, appointment_iso: str) -> Tuple[bool, Optional[float]]:
    """
    Check if driver is more than 30 minutes late based on GPS ETA vs appointment

    Args:
        gps_eta_iso: GPS-based ETA timestamp
        appointment_iso: Scheduled appointment time

    Returns:
        Tuple of (is_late, minutes_late) - minutes_late is None if not late or can't calculate
    """
    gps_dt = parse_iso_timestamp(gps_eta_iso)
    appt_dt = parse_iso_timestamp(appointment_iso)

    if not gps_dt or not appt_dt:
        return False, None

    # Calculate how late the driver is
    # Late = GPS ETA is after appointment time
    diff_seconds = (gps_dt - appt_dt).total_seconds()
    minutes_late = diff_seconds / 60

    if minutes_late > LATE_THRESHOLD_MINUTES:
        return True, round(minutes_late, 1)

    return False, None


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


def parse_iso_timestamp(iso_str: str) -> Optional[datetime]:
    """Parse ISO timestamp to datetime object"""
    if not iso_str:
        return None
    try:
        return datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def get_timezone_for_state(state: Optional[str]) -> ZoneInfo:
    """
    Get timezone for a US state code

    Args:
        state: Two-letter state code (e.g., "CA", "TX")

    Returns:
        ZoneInfo: Timezone object, defaults to America/Chicago if unknown
    """
    if not state:
        return ZoneInfo("America/Chicago")

    tz_name = STATE_TO_TIMEZONE.get(state.upper(), "America/Chicago")
    return ZoneInfo(tz_name)


def format_datetime_with_timezone(dt: datetime, state: Optional[str]) -> str:
    """
    Format datetime as "Jan 12, 19:59 EST" in the delivery location's timezone

    Args:
        dt: UTC datetime object
        state: Two-letter state code for timezone lookup

    Returns:
        str: Formatted datetime string like "Jan 12, 19:59 EST"
    """
    tz = get_timezone_for_state(state)
    local_dt = dt.astimezone(tz)

    # Format: "Jan 12, 19:59 EST"
    # %b = abbreviated month, %d = day, %H:%M = 24-hour time, %Z = timezone abbrev
    return local_dt.strftime("%b %d, %H:%M %Z")


def get_effective_delivery_time(
    eta_iso: str,
    appointment_iso: str,
    delivery_state: Optional[str]
) -> Tuple[Optional[str], Optional[str], Optional[float]]:
    """
    Get effective delivery time (later of GPS ETA or appointment)

    Returns the effective time as ISO string, formatted string, and hours until.

    Args:
        eta_iso: GPS-based ETA timestamp
        appointment_iso: Scheduled appointment time
        delivery_state: Two-letter state code for timezone formatting

    Returns:
        Tuple of (eta_iso, eta_formatted, hours_until) or (None, None, None) if invalid
    """
    eta_dt = parse_iso_timestamp(eta_iso)
    if not eta_dt:
        return None, None, None

    appointment_dt = parse_iso_timestamp(appointment_iso)

    # Use the LATER of ETA or appointment time
    if appointment_dt and appointment_dt > eta_dt:
        effective_time = appointment_dt
    else:
        effective_time = eta_dt

    # Calculate hours until
    now = datetime.now(timezone.utc)
    hours_until = round((effective_time - now).total_seconds() / 3600, 1)

    # Format the effective time
    eta_formatted = format_datetime_with_timezone(effective_time, delivery_state)

    return effective_time.isoformat(), eta_formatted, hours_until


def calculate_hours_until(eta_iso: str, appointment_iso: str = None) -> Optional[float]:
    """
    Calculate hours until delivery, using the LATER of ETA or appointment time

    This prevents premature calls when truck is close but appointment is later.
    Example: Truck 2 hours away, but appointment is tomorrow -> use tomorrow

    Args:
        eta_iso: GPS-based ETA timestamp (when truck will physically arrive)
        appointment_iso: Scheduled appointment time (when delivery is expected)

    Returns:
        float: Hours until effective delivery time (rounded to 1 decimal) or None
    """
    eta_dt = parse_iso_timestamp(eta_iso)
    if not eta_dt:
        return None

    appointment_dt = parse_iso_timestamp(appointment_iso)

    # Use the LATER of ETA or appointment time
    # If truck arrives early, they wait for appointment
    # If truck is late, they deliver when they arrive
    if appointment_dt and appointment_dt > eta_dt:
        effective_time = appointment_dt
    else:
        effective_time = eta_dt

    now = datetime.now(timezone.utc)
    hours = (effective_time - now).total_seconds() / 3600
    return round(hours, 1)


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
        dict: Owner name, email (team email format), phone
    """
    if not user_details:
        return {"name": None, "id": None, "email": None, "phone": None}

    # Generate team email from owner name: "Cameron Murray" -> "teammurray@motustrucking.com"
    owner_name = user_details.get("name", "")
    team_email = None
    if owner_name:
        name_parts = owner_name.strip().split()
        if name_parts:
            last_name = name_parts[-1].lower()
            team_email = f"team{last_name}@motustrucking.com"

    # Get team phone (prefer Fax type, which is the team line with extension)
    phones = user_details.get("phone", [])
    team_phone = None

    # First, look for Fax type (team line)
    for p in phones:
        if p.get("deleted"):
            continue
        if p.get("type", {}).get("value") == "Fax":
            team_phone = p.get("number")
            break

    # Fallback to primary if no Fax found
    if not team_phone:
        team_phone = next((p["number"] for p in phones if p.get("isPrimary") and not p.get("deleted")), None)

    return {
        "name": owner_name,
        "id": user_details.get("id"),
        "email": team_email,
        "phone": team_phone
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

    # Get ETA and appointment time
    eta_to_stop = delivery_stop.get("etaToStop", {})
    gps_eta_value = eta_to_stop.get("etaValue")
    miles_remaining = eta_to_stop.get("nextStopMiles")

    # Get appointment time (scheduled delivery window)
    appointment = delivery_stop.get("appointment", {})
    appointment_start = appointment.get("date")  # Turvo uses "date" not "startDate"

    if not gps_eta_value:
        print(f"⚠ Shipment {load_number}: No ETA available")
        return None

    # Get delivery state for timezone formatting
    delivery_address = delivery_stop.get("address", {})
    delivery_state = delivery_address.get("state")

    # Get effective delivery time (later of GPS ETA or appointment)
    # This prevents premature calls when truck is close but appointment is later
    eta_value, eta_formatted, hours_until = get_effective_delivery_time(
        gps_eta_value, appointment_start, delivery_state
    )

    if not eta_value:
        print(f"⚠ Shipment {load_number}: Could not parse ETA")
        return None

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
