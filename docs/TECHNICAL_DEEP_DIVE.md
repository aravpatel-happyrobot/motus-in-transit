# Technical Deep Dive: How This Works Under the Hood

This document explains exactly what's happening technically in the Motus Freight in-transit automation system.

---

## 1. **Authentication Flow (OAuth2 Password Grant)**

```python
POST https://publicapi.turvo.com/v1/oauth/token
Headers: {
    "Content-Type": "application/json",
    "x-api-key": "9CtJ7rMImv6BTB6x922xR6xDN6ckpiTG4FKrvbL1"
}
Body: {
    "grant_type": "password",  // OAuth2 password grant type
    "username": "support@happyrobot.ai",
    "password": "Yp9H49eJ$2m*2ds",
    "client_id": "publicapi",
    "client_secret": "secret",
    "scope": "read+trust+write",
    "type": "business"
}
```

**Response:**
```json
{
  "access_token": "3b_-06ff7030-48d6-4af8-a832-5df2314373c5",
  "token_type": "Bearer",
  "expires_in": 43198,  // ~12 hours
  "refresh_token": "81db8ffd-3946-47d0-981a-da2ac7cf1c8b"
}
```

**What's happening:**
- Using OAuth2 "password grant" (username + password → token)
- API returns a **Bearer token** valid for ~12 hours
- We include this token in `Authorization: Bearer {token}` for all subsequent requests
- The `x-api-key` is an additional API key requirement (Turvo-specific)

---

## 2. **Step 1: Query En Route Shipments (Lightweight List)**

```python
GET https://publicapi.turvo.com/v1/shipments/list?status[eq]=2105&pageSize=50
Headers: {
    "Authorization": "Bearer 3b_-06ff7030-...",
    "x-api-key": "9CtJ7rMImv6BTB6x922xR6xDN6ckpiTG4FKrvbL1",
    "Content-Type": "application/json"
}
```

**Why `status[eq]=2105`?**
- Turvo uses numeric status codes
- `2105` = "En route" status
- `[eq]` is a query operator (equals)

**Response Structure:**
```json
{
  "Status": "SUCCESS",
  "details": {
    "pagination": {
      "start": 10,
      "pageSize": 10,
      "totalRecordsInPage": 10,
      "moreAvailable": true  // More pages exist
    },
    "shipments": [
      {
        "id": 111537234,           // Shipment ID (we need this!)
        "customId": "M290969",      // Load number
        "status": {
          "code": {
            "key": "2105",
            "value": "En route"
          }
        },
        "customerOrder": [...],     // Customer info
        "carrierOrder": [...]       // Carrier info (minimal)
      },
      // ... more shipments
    ]
  }
}
```

**Key Point: This endpoint returns MINIMAL data**
- Just IDs, status, basic info
- **NO `globalRoute`** (stops/ETA data)
- **NO driver phone numbers**
- **NO detailed tracking info**

This is intentional - it's a lightweight list endpoint for querying/filtering.

---

## 3. **Step 2: Fetch Full Shipment Details (Per Shipment)**

For **each** shipment ID from step 1, we make another API call:

```python
GET https://publicapi.turvo.com/v1/shipments/111537234
Headers: {
    "Authorization": "Bearer 3b_-06ff7030-...",
    "x-api-key": "9CtJ7rMImv6BTB6x922xR6xDN6ckpiTG4FKrvbL1"
}
```

**This returns the FULL shipment object** (~500+ lines of JSON):

```json
{
  "Status": "SUCCESS",
  "details": {
    "id": 111537234,
    "customId": "M290969",
    "status": {
      "location": {
        "city": "Beckley, WV",
        "nextEta": "2 d 9 hs 15 min",
        "nextMiles": 2509
      }
    },
    "globalRoute": [          // ← THIS is what we need
      {
        "stopType": {"value": "Pickup"},
        "state": "COMPLETED",  // Already picked up
        "address": {
          "city": "Richmond",
          "state": "VA"
        },
        "attributes": {
          "arrival": "2026-01-02T15:32:49Z",
          "departed": "2026-01-02T18:08:48Z"
        }
      },
      {
        "stopType": {"value": "Delivery"},
        "state": "OPEN",       // Not delivered yet
        "etaToStop": {         // ← ETA DATA!
          "formattedEtaValue": "Jan 4, 23:37 PST",
          "etaValue": "2026-01-05T07:37:53Z",  // ISO 8601 timestamp
          "nextStopMiles": 2509                 // Miles remaining
        },
        "address": {
          "city": "Richland",
          "state": "WA",
          "line1": "2425 Stevens Dr"
        }
      }
    ],
    "carrierOrder": [
      {
        "deleted": false,
        "carrier": {
          "name": "Gns Trucking Inc",
          "id": 247689
        },
        "drivers": [           // ← DRIVER DATA!
          {
            "context": {
              "id": 14770956,
              "name": "Harrison",
              "phones": [
                {
                  "number": "5096552011",  // Driver phone!
                  "type": {"value": "Mobile"}
                }
              ]
            }
          }
        ]
      }
    ]
  }
}
```

**Why two API calls?**
- `/shipments/list` = Fast query/filter (returns IDs)
- `/shipments/{id}` = Get full details (heavy data)
- This pattern prevents over-fetching data

---

## 4. **Data Extraction Logic**

### A. Find the Delivery Stop

```python
def find_delivery_stop(global_route):
    for stop in global_route:
        # Check if it's a delivery stop
        if stop.get("stopType", {}).get("value") == "Delivery":
            # Check if it's still open (not delivered yet)
            if stop.get("state") == "OPEN":
                return stop
    return None
```

**What `state` means:**
- `"OPEN"` = Not completed yet
- `"COMPLETED"` = Already done
- `"CANCELLED"` = Cancelled

So we're looking for: **Delivery stop that hasn't been completed**

### B. Extract ETA Timestamp

```python
eta_to_stop = delivery_stop.get("etaToStop", {})
eta_value = eta_to_stop.get("etaValue")
# Returns: "2026-01-05T07:37:53Z"
```

**Format: ISO 8601 UTC timestamp**
- `2026-01-05` = Date
- `T` = Separator
- `07:37:53` = Time
- `Z` = Zulu time (UTC)

### C. Calculate Hours Until Delivery

```python
from datetime import datetime, timezone

def calculate_hours_until(eta_iso):
    # Parse ISO timestamp to datetime object
    eta_dt = datetime.fromisoformat(eta_iso.replace("Z", "+00:00"))
    # eta_dt = 2026-01-05 07:37:53 UTC

    # Get current time in UTC
    now = datetime.now(timezone.utc)
    # now = 2026-01-02 22:24:32 UTC

    # Calculate difference in seconds
    delta_seconds = (eta_dt - now).total_seconds()
    # delta_seconds = 206,121 seconds

    # Convert to hours
    hours = delta_seconds / 3600
    # hours = 57.26 hours

    return round(hours, 1)  # 57.3
```

**Why UTC?**
- Turvo returns timestamps in UTC
- Avoids timezone confusion
- Consistent calculations regardless of server location

### D. Extract Driver Phone

```python
def extract_driver_phone(shipment_details):
    carrier_orders = shipment_details.get("carrierOrder", [])

    for carrier_order in carrier_orders:
        # Skip deleted carrier assignments
        if carrier_order.get("deleted"):
            continue

        drivers = carrier_order.get("drivers", [])
        for driver in drivers:
            phones = driver.get("context", {}).get("phones", [])
            if phones:
                return phones[0].get("number")  # "5096552011"

    return None
```

**Why check `deleted`?**
- Turvo keeps history of carrier assignments
- A load might have been assigned to Carrier A, then reassigned to Carrier B
- Carrier A's assignment is marked `deleted: true`
- We only want the **current** (non-deleted) carrier's driver

---

## 5. **The Decision Logic**

```python
if hours_until_delivery <= 4 and not already_called:
    → Trigger call
else:
    → Skip
```

**Example from test:**
- Load M291033: `1.6 hours` until delivery → **CALL**
- Load M290389: `4.5 hours` until delivery → **SKIP**
- Load M286145: `48.0 hours` until delivery → **SKIP**

---

## 6. **Deduplication with Redis**

**Redis is an in-memory key-value database**

```python
import redis

redis_client = redis.from_url("redis://default:***@crossover.proxy.rlwy.net:43404")

# Before calling, check if already called
cache_key = f"motus:in_transit:{shipment_id}"
# cache_key = "motus:in_transit:111537234"

if redis_client.get(cache_key):
    # Key exists = already called this load
    continue  # Skip it

# After calling, mark as called
redis_client.set(
    cache_key,           # "motus:in_transit:111537234"
    "1",                 # Value (we just need existence, not value)
    ex=86400 * 30        # TTL = 30 days (in seconds)
)
```

**How Redis TTL works:**
- `ex=86400 * 30` = Expire after 2,592,000 seconds (30 days)
- After 30 days, the key automatically deletes
- This prevents calling the same load twice

**Why 30 days?**
- Loads typically deliver within days
- Prevents calling same load on repeat deliveries if they reuse shipment IDs
- Can be adjusted (7 days, 14 days, etc.)

---

## 7. **The Webhook POST**

When we find a load that needs a call:

```python
import requests

webhook_url = "https://workflows.platform.happyrobot.ai/hooks/..."

payload = {
    "load_number": "M291033",
    "shipment_id": 111537234,
    "driver_phone": "2106688527",
    "delivery_eta": "2026-01-03T00:06:23Z",
    "hours_until_delivery": 1.6,
    "miles_remaining": 97,
    "delivery_location": "New Oxford, PA",
    "source": "motus_in_transit"
}

response = requests.post(
    webhook_url,
    json=payload,
    headers={"Content-Type": "application/json"}
)
```

**What HappyRobot does:**
1. Receives this webhook
2. Extracts `driver_phone` and `delivery_eta`
3. Schedules an AI call to the driver
4. Asks: "Hi, this is Motus Freight. You're delivering to New Oxford, PA. What's your current ETA?"

---

## 8. **The Complete Flow (End-to-End)**

```
┌─────────────────────────────────────────────────────────────┐
│  CRON JOB triggers every 15 minutes                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  1. Authenticate with Turvo (OAuth2)                        │
│     → Get access token (valid 12 hours)                     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  2. GET /shipments/list?status[eq]=2105                     │
│     → Returns 24 En Route shipments (IDs only)              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  3. For EACH shipment ID:                                   │
│     ├─ GET /shipments/{id}                                  │
│     ├─ Extract globalRoute                                  │
│     ├─ Find delivery stop with state="OPEN"                 │
│     ├─ Get etaToStop.etaValue                               │
│     ├─ Calculate hours_until = (ETA - now) / 3600           │
│     └─ Extract driver phone from carrierOrder.drivers       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  4. Decision Logic:                                         │
│     IF hours_until <= 4:                                    │
│       ├─ Check Redis: "motus:in_transit:{id}" exists?      │
│       ├─ If NO → Continue to webhook                        │
│       └─ If YES → Skip (already called)                     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  5. POST webhook to HappyRobot                              │
│     {                                                       │
│       "driver_phone": "2106688527",                         │
│       "load_number": "M291033",                             │
│       "hours_until_delivery": 1.6                           │
│     }                                                       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  6. Mark in Redis (deduplication)                           │
│     SET "motus:in_transit:111537234" = "1" EX 2592000       │
└─────────────────────────────────────────────────────────────┘
```

---

## 9. **Performance Considerations**

**Current test:**
- 24 En Route shipments
- Made 10 individual `/shipments/{id}` calls
- Total time: ~5 seconds

**At scale (100 shipments):**
- 1 auth call
- 1 list call
- 100 detail calls = ~50 seconds

**Optimizations:**
- Parallel requests (async/await)
- Could reduce to ~10 seconds for 100 shipments
- Token caching (reuse for 12 hours)

**API Rate Limits:**
- Unknown (need to test)
- Can implement exponential backoff if we hit limits

---

## 10. **Why This Architecture Works**

**Advantages:**
1. **Real-time ETA** - Turvo tracks driver location, updates ETA
2. **No email parsing** - Direct API access
3. **Scalable** - Works for 10 or 1000 loads
4. **Reliable** - Redis prevents duplicates
5. **Timing precision** - Calculate exact hours until delivery

**Trade-offs:**
- Multiple API calls per poll (but fast enough)
- Need to handle pagination if >100 shipments
- Depends on Turvo's ETA accuracy (garbage in, garbage out)

---

## 11. **Data Flow Summary**

| Step | Action | Input | Output |
|------|--------|-------|--------|
| 1 | Authenticate | Username, Password | Bearer Token (12h) |
| 2 | List Shipments | `status[eq]=2105` | Array of shipment IDs |
| 3 | Get Details | Shipment ID | Full shipment object |
| 4 | Find Delivery | `globalRoute[]` | Delivery stop object |
| 5 | Extract ETA | `etaToStop.etaValue` | ISO timestamp |
| 6 | Calculate | ETA - Now | Hours until delivery |
| 7 | Check Redis | `motus:in_transit:{id}` | Exists? true/false |
| 8 | Post Webhook | Load data | HTTP 200 |
| 9 | Mark Called | Shipment ID | Redis key with TTL |

---

## 12. **Error Handling Considerations**

**What could go wrong:**

1. **Authentication fails**
   - Token expired
   - Wrong credentials
   - Solution: Retry auth, cache token

2. **Shipment has no globalRoute**
   - Data missing from Turvo
   - Solution: Skip, log warning

3. **No delivery stop found**
   - All stops completed or cancelled
   - Solution: Skip (load already delivered)

4. **No ETA available**
   - Driver not tracking
   - Solution: Skip or use scheduled time fallback

5. **No driver phone**
   - Not assigned yet
   - Solution: Skip or use carrier dispatch number

6. **Redis connection fails**
   - Network issue
   - Solution: Proceed anyway (risk duplicate calls)

---

## 13. **Configuration Variables**

```bash
# Turvo API
TURVO_BASE_URL=https://publicapi.turvo.com/v1
TURVO_API_KEY=9CtJ7rMImv6BTB6x922xR6xDN6ckpiTG4FKrvbL1
TURVO_USERNAME=support@happyrobot.ai
TURVO_PASSWORD=Yp9H49eJ$2m*2ds

# Business Logic
CALL_HOURS_THRESHOLD=4          # Call if ≤ 4 hours from delivery
POLL_INTERVAL_MINUTES=15        # Check every 15 minutes
REDIS_TTL_DAYS=30              # Remember calls for 30 days

# HappyRobot
MOTUS_IN_TRANSIT_WEBHOOK_URL=https://workflows.platform.happyrobot.ai/hooks/...

# Redis
REDIS_URL=redis://default:***@crossover.proxy.rlwy.net:43404
```

---

## 14. **Testing Strategy**

**Unit Tests:**
- `find_delivery_stop()` - Test with various globalRoute structures
- `calculate_hours_until()` - Test with different timestamps
- `extract_driver_phone()` - Test with missing/deleted carriers

**Integration Tests:**
- End-to-end workflow with real API
- Deduplication logic with Redis
- Webhook delivery

**Load Tests:**
- 100+ concurrent shipment detail fetches
- API rate limit testing

---

## 15. **Monitoring & Observability**

**Metrics to track:**
- Shipments processed per run
- Calls triggered per run
- API response times
- Redis hit rate (deduplication working?)
- Failed API calls
- Missing driver phone numbers

**Logs to capture:**
- Each poll execution
- Loads that triggered calls
- API errors
- Redis connection issues

---

**Last Updated:** 2026-01-02
**Status:** Tested & Validated
