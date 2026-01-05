# Webhook Payload Specification

## Complete Data Available from Turvo API

Based on testing, here's all the data we can include in the webhook payload to HappyRobot.

---

## Payload Structure

```json
{
  "load_number": "M290638",
  "shipment_id": 111484893,
  "driver_phone": "2092898301",
  "driver_name": "Harrison",

  "delivery_eta": "2026-01-03T00:06:23Z",
  "delivery_eta_formatted": "Jan 2, 19:06 EST",
  "hours_until_delivery": 1.6,
  "miles_remaining": 97,

  "pickup_location": {
    "name": "Fresh Express - Streamwood, IL",
    "city": "Streamwood",
    "state": "IL",
    "address": "1234 Main St"
  },

  "delivery_location": {
    "name": "Fresh Express Distribution",
    "city": "New Oxford",
    "state": "PA",
    "address": "5678 Delivery Rd"
  },

  "equipment": {
    "type": "Refrigerated",
    "size": "53 ft",
    "temp": 34,
    "temp_units": "°F",
    "description": "raw produce"
  },

  "notes": {
    "status": "per driver via phone LNR",
    "pickup": "TEAM DRIVERS ONLY!!! MUST DELIVER MONDAY!!",
    "delivery": "Ships 7-1 PM Strict cut off - CI is in the front office...",
    "equipment": "raw produce"
  },

  "carrier": {
    "name": "East Coast Express LLC",
    "id": 74412
  },

  "customer": {
    "name": "Fresh Express, INC",
    "id": 251166
  },

  "weight": 42000,
  "weight_units": "lb",

  "current_location": {
    "city": "Beckley",
    "state": "WV",
    "lat": 37.8674968,
    "lon": -81.2605913
  },

  "source": "motus_in_transit",
  "timestamp": "2026-01-02T22:24:32Z"
}
```

---

## Field Extraction Guide

### Basic Info
```python
load_number = shipment["customId"]              # "M290638"
shipment_id = shipment["id"]                     # 111484893
```

### Driver Info
```python
carrier_orders = shipment.get("carrierOrder", [])
for carrier_order in carrier_orders:
    if carrier_order.get("deleted"):
        continue

    # Carrier
    carrier_name = carrier_order.get("carrier", {}).get("name")
    carrier_id = carrier_order.get("carrier", {}).get("id")

    # Driver
    drivers = carrier_order.get("drivers", [])
    if drivers:
        driver = drivers[0]
        driver_name = driver.get("context", {}).get("name")
        driver_phone = driver.get("context", {}).get("phones", [{}])[0].get("number")
```

### Delivery ETA (from globalRoute)
```python
global_route = shipment.get("globalRoute", [])

# Find delivery stop
delivery_stop = None
for stop in global_route:
    if (stop.get("stopType", {}).get("value") == "Delivery" and
        stop.get("state") == "OPEN"):
        delivery_stop = stop
        break

if delivery_stop:
    eta_data = delivery_stop.get("etaToStop", {})
    eta_value = eta_data.get("etaValue")              # "2026-01-03T00:06:23Z"
    eta_formatted = eta_data.get("formattedEtaValue") # "Jan 2, 19:06 EST"
    miles_remaining = eta_data.get("nextStopMiles")   # 97

    # Delivery location
    address = delivery_stop.get("address", {})
    delivery_city = address.get("city")
    delivery_state = address.get("state")
    delivery_address = address.get("line1")
    delivery_name = delivery_stop.get("name")
```

### Pickup Info (from globalRoute)
```python
pickup_stop = None
for stop in global_route:
    if stop.get("stopType", {}).get("value") == "Pickup":
        pickup_stop = stop
        break

if pickup_stop:
    address = pickup_stop.get("address", {})
    pickup_city = address.get("city")
    pickup_state = address.get("state")
    pickup_address = address.get("line1")
    pickup_name = pickup_stop.get("name")
```

### Equipment (Including Temperature for Reefers)
```python
equipment = shipment.get("equipment", [])
if equipment:
    equip = equipment[0]

    equipment_type = equip.get("type", {}).get("value")      # "Refrigerated" or "Van"
    equipment_size = equip.get("size", {}).get("value")      # "53 ft"
    equipment_desc = equip.get("description")                # "raw produce"

    # Temperature (only for reefers)
    temp = equip.get("temp")                                 # 34 (or None if not reefer)
    temp_units = equip.get("tempUnits", {}).get("value")     # "°F"

    # Weight
    weight = equip.get("weight")                             # 42000
    weight_units = equip.get("weightUnits", {}).get("value") # "lb"
```

### Notes (Multiple Levels)
```python
notes = {}

# Status notes
notes["status"] = shipment.get("status", {}).get("notes")

# Pickup notes
if pickup_stop:
    notes["pickup"] = pickup_stop.get("notes")

# Delivery notes
if delivery_stop:
    notes["delivery"] = delivery_stop.get("notes")

# Equipment notes
if equipment:
    notes["equipment"] = equipment[0].get("description")
```

### Customer Info
```python
customer_orders = shipment.get("customerOrder", [])
if customer_orders:
    customer = customer_orders[0].get("customer", {})
    customer_name = customer.get("name")  # "Fresh Express, INC"
    customer_id = customer.get("id")      # 251166
```

### Current Location (from status)
```python
status_location = shipment.get("status", {}).get("location", {})

current_city = status_location.get("city")
current_state = status_location.get("state")
current_lat = status_location.get("lat")
current_lon = status_location.get("lon")
```

---

## Temperature Handling Logic

```python
def get_temperature_info(shipment):
    """
    Extract temperature information if this is a reefer load
    Returns None if not a temperature-controlled load
    """
    equipment = shipment.get("equipment", [])
    if not equipment:
        return None

    equip = equipment[0]
    equip_type = equip.get("type", {}).get("value", "")

    # Check if it's a refrigerated load
    if "Refrigerated" in equip_type or "Reefer" in equip_type:
        temp = equip.get("temp")
        if temp is not None:
            temp_units = equip.get("tempUnits", {}).get("value", "°F")
            return {
                "temperature": temp,
                "units": temp_units,
                "description": equip.get("description")
            }

    return None

# Usage in webhook payload
temp_info = get_temperature_info(shipment)
if temp_info:
    payload["equipment"]["temp"] = temp_info["temperature"]
    payload["equipment"]["temp_units"] = temp_info["units"]
```

---

## Example Use Cases for Notes

**Pickup Notes:**
```
"TEAM DRIVERS ONLY!!! MUST DELIVER MONDAY!!"
```
→ AI can mention: "I see this requires team drivers and Monday delivery"

**Delivery Notes:**
```
"Ships 7-1 PM Strict cut off - CI is in the front office with Trent..."
```
→ AI can ask: "Are you aware of the 7-1 PM cutoff time?"

**Status Notes:**
```
"per driver via phone LNR"
```
→ Indicates last check-in was by phone

---

## Example Use Cases for Temperature

**For Reefer Loads:**
```json
{
  "equipment": {
    "type": "Refrigerated",
    "temp": 34,
    "temp_units": "°F"
  }
}
```

→ AI can ask: "Can you confirm the trailer is maintaining 34 degrees?"

**For Non-Reefer Loads:**
```json
{
  "equipment": {
    "type": "Van",
    "temp": null
  }
}
```
→ No temperature question needed

---

## Recommended Webhook Payload (Minimal)

If you want to keep the payload lean:

```json
{
  "load_number": "M290638",
  "shipment_id": 111484893,
  "driver_phone": "2092898301",
  "driver_name": "Harrison",
  "hours_until_delivery": 1.6,
  "delivery_location": "New Oxford, PA",
  "delivery_eta": "Jan 2, 19:06 EST",
  "miles_remaining": 97,
  "temperature": 34,           // null if not reefer
  "temp_units": "°F",          // null if not reefer
  "notes": "TEAM DRIVERS ONLY!!! MUST DELIVER MONDAY!!",
  "source": "motus_in_transit"
}
```

---

## Recommended Webhook Payload (Full)

Include everything for maximum context:

```json
{
  "load_number": "M290638",
  "shipment_id": 111484893,

  "driver": {
    "name": "Harrison",
    "phone": "2092898301"
  },

  "delivery": {
    "eta": "2026-01-03T00:06:23Z",
    "eta_formatted": "Jan 2, 19:06 EST",
    "hours_until": 1.6,
    "miles_remaining": 97,
    "location": {
      "name": "Fresh Express Distribution",
      "city": "New Oxford",
      "state": "PA",
      "address": "5678 Delivery Rd"
    },
    "notes": "Ships 7-1 PM Strict cut off..."
  },

  "pickup": {
    "location": {
      "name": "Fresh Express - Streamwood, IL",
      "city": "Streamwood",
      "state": "IL"
    },
    "notes": "TEAM DRIVERS ONLY!!! MUST DELIVER MONDAY!!"
  },

  "equipment": {
    "type": "Refrigerated",
    "size": "53 ft",
    "temperature": 34,
    "temp_units": "°F",
    "description": "raw produce",
    "weight": 42000,
    "weight_units": "lb"
  },

  "current_location": {
    "city": "Beckley",
    "state": "WV"
  },

  "carrier": {
    "name": "East Coast Express LLC"
  },

  "customer": {
    "name": "Fresh Express, INC"
  },

  "source": "motus_in_transit",
  "timestamp": "2026-01-02T22:24:32Z"
}
```

---

**Last Updated:** 2026-01-02
