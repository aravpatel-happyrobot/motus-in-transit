# HappyRobot Workflow Design

**Integration:** Motus Freight In-Transit Calls
**Webhook URL:** `https://workflows.platform.happyrobot.ai/hooks/pye5hnn9s04h/jlm0wco8szzd`
**Last Updated:** January 8, 2026

---

## Call Windows

| Window | Timing | Purpose |
|--------|--------|---------|
| **Checkin** | 3-4 hours before delivery | Proactive check on ETA, location, reefer temp |
| **Final** | 0-30 minutes before delivery | Quick confirmation before arrival |

---

## Workflow Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    HAPPYROBOT WORKFLOW                          │
└─────────────────────────────────────────────────────────────────┘

  ┌──────────────┐
  │   Webhook    │ ← POST from Railway (batch of shipments)
  └──────┬───────┘
         │
         ▼
  ┌──────────────┐
  │ Make parallel│ ← For each shipment in batch
  │ calls        │
  └──────┬───────┘
         │
         ▼
  ┌──────────────┐
  │ Format Load  │ ← Strip "M" prefix (M292458 → 292458)
  │ Number       │
  └──────┬───────┘
         │
         ▼
  ┌──────────────┐
  │ Find load by │ ← Enrich from HappyRobot DB
  │ reference    │
  └──────┬───────┘
         │
         ▼
  ┌──────────────┐
  │   Branch:    │ ← Route by call_type
  │  call_type   │
  └──────┬───────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌───────┐ ┌───────┐
│checkin│ │ final │
│ agent │ │ agent │
└───┬───┘ └───┬───┘
    │         │
    └────┬────┘
         │
         ▼
  ┌──────────────┐
  │  Post-Call   │ ← Handle results, alerts, logging
  │  Processing  │
  └──────────────┘
```

---

## Node 1: Webhook (Incoming Hook)

### What Railway Sends

```json
{
  "shipments": [
    { /* shipment 1 */ },
    { /* shipment 2 */ },
    // ... up to N shipments
  ],
  "total_calls": 14,
  "checkin_calls": 3,
  "final_calls": 11,
  "timestamp": "2026-01-08T16:19:44Z"
}
```

### Single Shipment Object Structure

```json
{
  "load_number": "M292458",
  "shipment_id": 111809552,
  "call_type": "final",

  "driver": {
    "name": "Frankely",
    "phone": "8566686958"
  },

  "delivery": {
    "eta": "2026-01-08T16:38:00Z",
    "eta_formatted": "11:38 EST",
    "hours_until": 0.3,
    "miles_remaining": 36,
    "location": {
      "name": "United Scrap Metal - Philadelphia, PA",
      "city": "Philadelphia",
      "state": "PA",
      "address": "4301 Wissahickon Ave"
    }
  },

  "pickup": {
    "location": {
      "name": "PPL Whemp - Hummellsville",
      "city": "Elizabethtown",
      "state": "PA",
      "address": "3085 Colebrook Rd"
    }
  },

  "equipment": {
    "type": "Step deck",
    "size": null,
    "temperature": null,
    "temp_units": null,
    "weight": 20000,
    "weight_units": "lb",
    "description": null
  },

  "notes": {
    "status": null,
    "pickup": "Kyle 717-736-9383",
    "delivery": null,
    "equipment": null
  },

  "carrier": {
    "name": "JAY NATIONAL TRANSPORTATION LLC",
    "id": 8023662
  },

  "customer": {
    "name": "United Scrap Metal Inc",
    "id": 7826327
  },

  "source": "motus_in_transit",
  "timestamp": "2026-01-08T16:17:47Z"
}
```

### Key Fields for Voice Agent

| Field | Path | Example | Use For |
|-------|------|---------|---------|
| Call type | `call_type` | `"checkin"` or `"final"` | Branching logic |
| Driver name | `driver.name` | `"Frankely"` | Greeting |
| Driver phone | `driver.phone` | `"8566686958"` | Dial this number |
| Load number | `load_number` | `"M292458"` | Reference in call |
| ETA | `delivery.eta_formatted` | `"11:38 EST"` | Tell driver their ETA |
| Miles out | `delivery.miles_remaining` | `36` | "You're about 36 miles out" |
| Hours until | `delivery.hours_until` | `0.3` | Context for urgency |
| Destination city | `delivery.location.city` | `"Philadelphia"` | Reference location |
| Destination state | `delivery.location.state` | `"PA"` | Reference location |
| Is reefer? | `equipment.temperature` | `28` or `null` | Ask for temp if not null |
| Reefer temp | `equipment.temperature` | `28` | Current reading from GPS |
| Delivery notes | `notes.delivery` | Instructions | Context for agent |

---

## Node 2: Make Parallel Calls (Code Node)

Splits the batch into individual parallel executions.

```javascript
// Input: $input.body.shipments (array)
// Output: One execution per shipment

return $input.body.shipments.map((shipment, index) => ({
  shipment: shipment,
  index: index
}));
```

---

## Node 3: Format Load Number (Code Node)

Strips the "M" prefix for database lookup.

```javascript
// Input: shipment.load_number = "M292458"
// Output: "292458"

const loadNumber = $item.shipment.load_number;
const formattedNumber = loadNumber.replace(/^M/, '');

return {
  ...data,
  formatted_load_number: formattedNumber
};
```

---

## Node 4: Find Load by Reference (Turvo/DB Lookup)

Queries your HappyRobot database using the formatted load number.

### What You Get Back (Enriched Data)

```json
{
  "load": {
    "id": "4f3a64aa-cdeb-47c3-9e92-22be77344225",
    "custom_load_id": "292458",
    "status": "En_route",

    "carrier": {
      "name": "Jay National Transportation",
      "dot_number": "3433927",
      "mc_number": "1113380"
    },

    "carrier_contacts": [
      {
        "contact": {
          "name": "Frankely",
          "phone": "8566686958",
          "email": "jaynational1018@gmail.com",
          "type": "driver"
        }
      }
    ],

    "commodity_type": "Aluminum Cable Reel",

    "destination_location": {
      "city": "philadelphia",
      "state": "PA",
      "address": "4301 Wissahickon Ave",
      "lat": 40.01358,
      "lon": -75.18461
    },

    "origin_location": {
      "city": "hummelstown",
      "state": "PA"
    },

    "stops": [
      { "type": "pick", "address": "...", "notes": "..." },
      { "type": "drop", "address": "...", "notes": "..." }
    ],

    "delivery_date_open": "2026-01-08T06:00:00",
    "delivery_date_close": "2026-01-08T16:30:00",

    "miles": 104,
    "weight": null,
    "equipment_type_name": "Step deck",

    "sale_notes": "Stop ?: Kyle 717-736-9383 | Stop ?: Kyle 717-736-9383"
  }
}
```

### Useful Fields from DB Lookup

| Field | Path | Use For |
|-------|------|---------|
| Carrier name | `load.carrier.name` | Context |
| Carrier DOT | `load.carrier.dot_number` | Reference |
| Commodity | `load.commodity_type` | What they're hauling |
| Total miles | `load.miles` | Full route distance |
| Delivery window | `load.delivery_date_close` | Appointment time |
| Sale notes | `load.sale_notes` | Special instructions |

---

## Node 5: Branch on call_type

Route to different voice agents based on call type.

### Condition

```javascript
// If checkin call
$item.shipment.call_type === "checkin"  →  Checkin Agent

// If final call
$item.shipment.call_type === "final"    →  Final Agent
```

---

## Node 6a: Voice Agent - Checkin (3-4 Hours Before)

### Purpose
Proactive check-in to confirm ETA, location, and reefer temperature.

### Phone Configuration
- **Dial:** `{{ $item.shipment.driver.phone }}`

### Context Variables to Inject

```javascript
{
  // Call info
  call_type: "checkin",

  // Load reference
  load_number: $item.shipment.load_number,           // "M292458"

  // Driver
  driver_name: $item.shipment.driver.name,           // "Frankely"

  // Destination
  destination_city: $item.shipment.delivery.location.city,    // "Philadelphia"
  destination_state: $item.shipment.delivery.location.state,  // "PA"
  destination_name: $item.shipment.delivery.location.name,    // "United Scrap Metal"

  // ETA & Distance (from real-time GPS)
  eta_formatted: $item.shipment.delivery.eta_formatted,       // "11:38 EST"
  hours_until: $item.shipment.delivery.hours_until,           // 3.5
  miles_remaining: $item.shipment.delivery.miles_remaining,   // 228

  // Equipment
  is_reefer: $item.shipment.equipment.temperature !== null,   // true/false
  current_reefer_temp: $item.shipment.equipment.temperature,  // 28 or null
  equipment_type: $item.shipment.equipment.type,              // "Refrigerated"

  // Notes
  delivery_notes: $item.shipment.notes.delivery,

  // From DB lookup (enriched)
  carrier_name: $db.load.carrier.name,                        // "Jay National Transportation"
  commodity: $db.load.commodity_type,                         // "Aluminum Cable Reel"
  appointment_time: $db.load.delivery_date_close              // "2026-01-08T16:30:00"
}
```

### Sample Checkin Prompt

```
You are a dispatcher assistant for Motus Freight making a check-in call to a truck driver.

SHIPMENT INFORMATION:
- Load Number: {{ load_number }}
- Driver Name: {{ driver_name }}
- Carrier: {{ carrier_name }}
- Hauling: {{ commodity }}
- Destination: {{ destination_name }} in {{ destination_city }}, {{ destination_state }}
- Current ETA: {{ eta_formatted }}
- Miles Remaining: {{ miles_remaining }} miles
- Equipment Type: {{ equipment_type }}
- Is Refrigerated: {{ is_reefer }}
- Current Reefer Temp: {{ current_reefer_temp }}°F

DELIVERY NOTES:
{{ delivery_notes }}

YOUR CONVERSATION FLOW:

1. GREETING
   "Hi, is this {{ driver_name }}?"
   [Wait for confirmation]

2. INTRODUCTION
   "This is [Agent Name] calling from Motus Freight about load {{ load_number }}."

3. ETA CHECK
   "You're heading to {{ destination_city }} - your ETA shows {{ eta_formatted }},
    about {{ miles_remaining }} miles out. Are you still on track for that time?"
   [Listen for: confirmed, delayed, or new ETA]

4. LOCATION CHECK
   "And where are you right now?"
   [Listen for: city, highway, landmark]

5. IF REFRIGERATED (is_reefer is true):
   "What's your current reefer temperature reading?"
   [Listen for: temperature number]

6. ISSUES CHECK
   "Any issues or concerns I should know about?"
   [Listen for: mechanical, traffic, weather, delays]

7. CLOSING
   "Great, thank you {{ driver_name }}! Safe travels."

INFORMATION TO COLLECT:
- confirmed_eta: The ETA they confirm OR a new ETA if delayed
- current_location: Where they say they are (city, highway, etc.)
- reefer_temp: Temperature reading (if refrigerated load)
- issues: Any problems or concerns mentioned (or null if none)
- call_outcome: "completed", "no_answer", "voicemail", "wrong_number"
```

### Expected Output

```json
{
  "call_outcome": "completed",
  "confirmed_eta": "11:38 EST",
  "current_location": "About 30 miles out on I-76",
  "reefer_temp": 28,
  "issues": null,
  "call_duration_seconds": 52,
  "transcript": "..."
}
```

---

## Node 6b: Voice Agent - Final (0-30 Minutes Before)

### Purpose
Quick final confirmation when driver is almost at delivery.

### Phone Configuration
- **Dial:** `{{ $item.shipment.driver.phone }}`

### Context Variables to Inject

```javascript
{
  // Call info
  call_type: "final",

  // Load reference
  load_number: $item.shipment.load_number,           // "M292458"

  // Driver
  driver_name: $item.shipment.driver.name,           // "Frankely"

  // Destination
  destination_city: $item.shipment.delivery.location.city,    // "Philadelphia"
  destination_name: $item.shipment.delivery.location.name,    // "United Scrap Metal"
  destination_address: $item.shipment.delivery.location.address, // "4301 Wissahickon Ave"

  // Distance (real-time)
  miles_remaining: $item.shipment.delivery.miles_remaining,   // 7

  // Equipment
  is_reefer: $item.shipment.equipment.temperature !== null,
  current_reefer_temp: $item.shipment.equipment.temperature,

  // Notes
  delivery_notes: $item.shipment.notes.delivery
}
```

### Sample Final Prompt

```
You are a dispatcher assistant for Motus Freight making a quick final check before delivery.

SHIPMENT INFORMATION:
- Load Number: {{ load_number }}
- Driver Name: {{ driver_name }}
- Destination: {{ destination_name }}
- Address: {{ destination_address }}, {{ destination_city }}
- Miles Remaining: {{ miles_remaining }} miles
- Is Refrigerated: {{ is_reefer }}
- Current Reefer Temp: {{ current_reefer_temp }}°F

DELIVERY NOTES:
{{ delivery_notes }}

YOUR CONVERSATION FLOW:

1. QUICK GREETING
   "Hi {{ driver_name }}, quick call from Motus about load {{ load_number }}."

2. ARRIVAL CHECK
   "You should be arriving at {{ destination_city }} shortly - are you there or almost there?"
   [Listen for: "at facility", "pulling in", "X minutes away"]

3. IF REFRIGERATED (is_reefer is true):
   "What's your final reefer temp?"
   [Listen for: temperature number]

4. ISSUES CHECK
   "Any issues at delivery?"
   [Listen for: problems or "no"]

5. QUICK CLOSE
   "Thanks {{ driver_name }}, good luck with the delivery!"

KEEP THIS CALL SHORT - Driver is about to deliver.

INFORMATION TO COLLECT:
- arrival_status: "at_facility", "pulling_in", "X_minutes_away", "delayed"
- final_reefer_temp: Temperature reading (if refrigerated)
- issues: Any problems (or null)
- call_outcome: "completed", "no_answer", "voicemail", "wrong_number"
```

### Expected Output

```json
{
  "call_outcome": "completed",
  "arrival_status": "pulling_in",
  "final_reefer_temp": 27,
  "issues": null,
  "call_duration_seconds": 28,
  "transcript": "..."
}
```

---

## Node 7: Post-Call Processing

Handle the results from the voice agent.

### Logic Flow

```javascript
const result = $voiceAgent.output;
const shipment = $item.shipment;
const callType = shipment.call_type;

// 1. Log the call
console.log(`${shipment.load_number} [${callType}]: ${result.call_outcome}`);

// 2. Handle based on outcome
if (result.call_outcome === "completed") {

  // Check reefer temp alerts
  if (shipment.equipment.temperature !== null) {
    const temp = result.reefer_temp || result.final_reefer_temp;

    if (temp > 40) {
      // ALERT: Reefer temp too high!
      await sendAlert({
        type: "REEFER_HIGH",
        load: shipment.load_number,
        temp: temp,
        threshold: 40,
        driver: shipment.driver.name,
        phone: shipment.driver.phone
      });
    }

    if (temp < 20) {
      // ALERT: Reefer temp too low (freezing risk)
      await sendAlert({
        type: "REEFER_LOW",
        load: shipment.load_number,
        temp: temp,
        driver: shipment.driver.name
      });
    }
  }

  // Check for reported issues
  if (result.issues) {
    await createTask({
      type: "DRIVER_ISSUE",
      load: shipment.load_number,
      issue: result.issues,
      driver: shipment.driver.name,
      phone: shipment.driver.phone,
      call_type: callType
    });
  }

  // Optional: Update database with results
  await updateLoadStatus({
    load_id: shipment.shipment_id,
    last_checkin: new Date().toISOString(),
    confirmed_eta: result.confirmed_eta || result.arrival_status,
    reefer_temp: result.reefer_temp || result.final_reefer_temp,
    driver_location: result.current_location
  });

} else if (result.call_outcome === "no_answer") {
  // Log for potential retry or manual follow-up
  console.log(`No answer for ${shipment.load_number} - may retry`);

} else if (result.call_outcome === "wrong_number") {
  // Flag for data quality review
  await createTask({
    type: "DATA_QUALITY",
    load: shipment.load_number,
    issue: "Wrong phone number for driver",
    phone: shipment.driver.phone
  });
}
```

### Branching by Outcome

| Outcome | Action |
|---------|--------|
| `completed` - no issues | Log success, update DB |
| `completed` - issue reported | Create human task, notify team |
| `completed` - reefer temp high | Immediate alert |
| `no_answer` | Log, optionally retry |
| `voicemail` | Log as attempted |
| `wrong_number` | Flag for data quality |

---

## Reefer Temperature Thresholds

| Range | Status | Action |
|-------|--------|--------|
| 20-40°F | Normal | Log only |
| > 40°F | HIGH | Alert - product warming |
| > 45°F | CRITICAL | Urgent alert - product at risk |
| < 20°F | LOW | Alert - freezing risk |

*Note: Actual thresholds depend on commodity. Fresh produce may need tighter ranges than frozen goods.*

---

## Testing the Workflow

### Manual Test Payload

Send this to your webhook to test without Railway:

```json
{
  "shipments": [
    {
      "load_number": "M999999",
      "shipment_id": 999999,
      "call_type": "checkin",
      "driver": {
        "name": "Test Driver",
        "phone": "YOUR_TEST_PHONE_HERE"
      },
      "delivery": {
        "eta": "2026-01-08T20:00:00Z",
        "eta_formatted": "3:00 PM EST",
        "hours_until": 3.5,
        "miles_remaining": 150,
        "location": {
          "name": "Test Facility",
          "city": "Atlanta",
          "state": "GA",
          "address": "123 Test St"
        }
      },
      "pickup": {
        "location": {
          "city": "Miami",
          "state": "FL"
        }
      },
      "equipment": {
        "type": "Refrigerated",
        "temperature": 34,
        "temp_units": "F"
      },
      "notes": {
        "delivery": "Call receiver 30 min before arrival"
      },
      "carrier": {
        "name": "Test Carrier"
      },
      "customer": {
        "name": "Test Customer"
      },
      "source": "motus_in_transit",
      "timestamp": "2026-01-08T16:30:00Z"
    }
  ],
  "total_calls": 1,
  "checkin_calls": 1,
  "final_calls": 0,
  "timestamp": "2026-01-08T16:30:00Z"
}
```

---

## Data Flow Summary

```
RAILWAY (Real-time GPS data)          HAPPYROBOT DB (Enriched data)
─────────────────────────────         ────────────────────────────
✓ driver.name                         ✓ carrier.name
✓ driver.phone                        ✓ carrier.dot_number
✓ delivery.eta_formatted              ✓ commodity_type
✓ delivery.miles_remaining            ✓ stops[] with notes
✓ delivery.hours_until                ✓ delivery_date_close (appt)
✓ delivery.location.*                 ✓ sale_notes
✓ equipment.temperature               ✓ total miles
✓ notes.delivery                      ✓ lat/lon coordinates
✓ call_type (checkin/final)
```

---

## Troubleshooting

| Issue | Possible Cause | Solution |
|-------|----------------|----------|
| No calls triggered | No loads in window | Check current ETAs |
| Same load called twice | Redis not working | Check Redis connection |
| Missing driver phone | Bad Turvo data | Logged as "missing data" |
| Wrong reefer temp | GPS sensor issue | Driver confirms verbally |
| Webhook not received | URL changed | Check Railway env vars |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-08 | Initial design |
| 1.1 | 2026-01-08 | Added HappyRobot-specific workflow, DB lookup details, updated prompts |
