# Turvo Integration Implementation Plan for Motus Freight

## Overview
This document outlines the plan to build an in-transit automation system for Motus Freight using the Turvo TMS API, based on the existing McLeod integration patterns from Peach State.

---

## Current State Analysis

### What We Have (Peach State / Meiborg)
- **TMS:** McLeod (API-based polling)
- **Architecture:** FastAPI server with scheduled cron jobs
- **Components:**
  - Find Load API (on-demand search)
  - Pre-Pickup Handler (hourly, calls 1-2 hours before pickup)
  - In-Transit Handler (2x daily check-ins at 9 AM & 2 PM)
  - Redis deduplication
  - Data transformation layer
  - Webhook integration with HappyRobot

### What We Need (Motus Freight)
- **TMS:** Turvo (REST API with OAuth2)
- **Architecture:** Same FastAPI pattern
- **Key Difference:** Turvo has different data structure, status codes, and authentication method

---

## Implementation Strategy

### Option A: Separate Integration (RECOMMENDED)
Create a completely separate integration for Motus Freight alongside the existing Peach State integration.

**Pros:**
- Clean separation of concerns
- No risk to existing Peach State production system
- Can iterate independently
- Different deployment schedules

**Cons:**
- Some code duplication
- Two separate servers to maintain

**Structure:**
```
/motus-in-transit/
└── integrations/
    ├── meiborg_brothers/    # Existing (Peach State + McLeod)
    │   └── [keep as-is]
    └── motus_freight/       # New (Motus + Turvo)
        ├── server.py
        ├── requirements.txt
        ├── railway.json
        └── handlers/
            ├── turvo_client.py
            ├── turvo_utils.py
            ├── pre_delivery.py
            ├── in_transit.py
            ├── models.py
            └── redis_client.py
```

### Option B: Unified Integration
Refactor to support multiple clients and TMS systems in one codebase.

**Pros:**
- Less code duplication
- Shared utilities and patterns

**Cons:**
- Higher risk of breaking existing system
- More complex configuration
- Harder to debug client-specific issues

**Recommendation:** Start with Option A, refactor to Option B later if needed.

---

## Turvo API Integration Plan

### Phase 1: API Discovery & Testing (THIS PHASE)

**Goals:**
- Verify Turvo API authentication works
- Test shipment listing with various filters
- Understand response data structure
- Validate key fields are available:
  - Driver phone numbers
  - ETA to delivery
  - Current location
  - Miles remaining
  - Status codes

**Deliverables:**
- `turvo_api_test.py` - Test script with multiple queries
- `TURVO_API_ANALYSIS.md` - Documentation of findings
- Sample JSON responses saved for reference

**Key Tests:**
1. OAuth2 authentication flow
2. List shipments by status (En Route = 2105)
3. Filter by delivery date range
4. Extract ETA and distance information
5. Verify driver contact information availability

---

### Phase 2: Core Infrastructure Setup

**Tasks:**
1. **Create Project Structure**
   ```bash
   mkdir -p integrations/motus_freight/handlers
   touch integrations/motus_freight/{server.py,requirements.txt,railway.json}
   touch integrations/motus_freight/handlers/{__init__.py,turvo_client.py,turvo_utils.py,models.py}
   ```

2. **Environment Configuration**
   Add to `.env`:
   ```bash
   # Turvo API Configuration
   TURVO_BASE_URL=https://publicapi.turvo.com/v1
   TURVO_API_KEY=9CtJ7rMImv6BTB6x922xR6xDN6ckpiTG4FKrvbL1
   TURVO_USERNAME=support@happyrobot.ai
   TURVO_PASSWORD=<password>
   TURVO_CLIENT_ID=publicapi
   TURVO_CLIENT_SECRET=secret

   # Motus Freight Webhooks
   MOTUS_PRE_DELIVERY_WEBHOOK_URL=<webhook_url>
   MOTUS_IN_TRANSIT_WEBHOOK_URL=<webhook_url>

   # Redis (shared)
   REDIS_URL=redis://default:***@crossover.proxy.rlwy.net:43404
   ```

3. **Create Turvo API Client** (`turvo_client.py`)
   - OAuth2 token management with caching
   - Token refresh logic
   - Base request methods (GET, POST)
   - Error handling for Turvo-specific errors
   - Rate limiting awareness

4. **Create Data Models** (`models.py`)
   ```python
   class TurvoShipment(BaseModel):
       id: str
       customId: str  # Load number
       status: dict
       globalRoute: List[dict]
       carrierOrder: List[dict]
       # ... etc

   class HappyRobotLoadEvent(BaseModel):
       order_id: str
       movement_id: Optional[str]
       driver_phone: str
       delivery_eta: str
       miles_remaining: Optional[float]
       # ... standardized format
   ```

---

### Phase 3: Data Transformation Layer

**Create `turvo_utils.py`** (similar to `find_load_utils.py`)

**Key Mappings:**

| McLeod Field | Turvo Field | Notes |
|--------------|-------------|-------|
| `order.id` | `shipment.customId` | Load number |
| `movement.id` | `shipment.carrierOrder[0].id` | Carrier assignment |
| `brokerage_status` | `shipment.status.code.value` | Status enum (2105 = En Route) |
| `stops[0].sched_arrive_early` | `globalRoute[0].etaToStop.etaValue` | Pickup time |
| `stops[-1].sched_arrive_early` | `globalRoute[-1].etaToStop.etaValue` | Delivery ETA |
| `movement.override_drvr_cell` | `carrierOrder[0].drivers[0].phone.number` | Driver phone |
| `stops[].city_name` | `globalRoute[].address.city` | Location |

**Functions to implement:**
```python
def transform_turvo_shipment(turvo_data: dict) -> HappyRobotLoadEvent:
    """Transform Turvo shipment to standardized format"""
    pass

def parse_turvo_timestamp(timestamp: str) -> str:
    """Convert Turvo ISO8601 to standard format"""
    pass

def extract_delivery_stop(global_route: List[dict]) -> dict:
    """Find the delivery stop from route"""
    pass

def calculate_hours_until_delivery(eta: str) -> float:
    """Calculate time remaining to delivery"""
    pass
```

---

### Phase 4: Pre-Delivery Handler

**Create `pre_delivery.py`** (equivalent to `pre_pickup.py`)

**Purpose:** Call drivers 3 hours before delivery (not pickup!)

**Polling Strategy:**
- **Frequency:** Every 15-30 minutes
- **Query Window:** Shipments delivering in next 24 hours
- **Status Filter:** `status[eq]=2105` (En Route)

**Logic:**
```python
@router.post("/sync-pre-delivery")
async def sync_pre_delivery():
    # 1. Get OAuth token
    token = await turvo_client.get_access_token()

    # 2. Query Turvo API
    now = datetime.now(timezone.utc)
    tomorrow = now + timedelta(days=1)

    params = {
        "status[eq]": 2105,  # En Route
        "deliveryDate[gte]": now.isoformat(),
        "deliveryDate[lte]": tomorrow.isoformat(),
        "pageSize": 50
    }

    shipments = await turvo_client.list_shipments(params)

    # 3. Filter for shipments 3 hours from delivery
    CALL_HOURS_BEFORE = 3
    calls_to_make = []

    for shipment in shipments:
        delivery_stop = extract_delivery_stop(shipment["globalRoute"])
        if not delivery_stop:
            continue

        eta = delivery_stop["etaToStop"]["etaValue"]
        hours_until = calculate_hours_until_delivery(eta)

        # Call window: 2.5 to 3.5 hours before delivery
        if 2.5 <= hours_until <= 3.5:
            # Check Redis deduplication
            cache_key = f"motus:pre_delivery:{shipment['id']}"
            if redis_client.get(cache_key):
                continue  # Already called

            calls_to_make.append(shipment)

    # 4. Send webhooks
    for shipment in calls_to_make:
        payload = transform_turvo_shipment(shipment)
        await send_webhook(MOTUS_PRE_DELIVERY_WEBHOOK_URL, payload)

        # Mark as called
        redis_client.set(
            f"motus:pre_delivery:{shipment['id']}",
            json.dumps({"called_at": now.isoformat()}),
            ex=86400 * 7  # 7 day TTL
        )

    return {"success": True, "calls_scheduled": len(calls_to_make)}
```

**Key Differences from Peach State Pre-Pickup:**
- Calls BEFORE DELIVERY (not pickup)
- Uses Turvo ETA data (not scheduled time)
- Filters by `status=2105` (En Route) not COVERED
- Checks miles remaining for additional validation

---

### Phase 5: In-Transit Handler

**Create `in_transit.py`**

**Purpose:** Scheduled check-in calls for loads in transit

**Polling Strategy:**
- **Frequency:** 2x daily (9 AM & 2 PM Central)
- **Query Window:** All shipments in En Route status
- **Deduplication:** One call per shipment per day

**Logic:**
```python
@router.post("/sync-in-transit")
async def sync_in_transit():
    token = await turvo_client.get_access_token()

    # Query all En Route shipments
    params = {
        "status[eq]": 2105,  # En Route
        "pageSize": 100
    }

    shipments = await turvo_client.list_shipments(params)

    # Filter: Picked up but not delivered
    in_transit = []
    for shipment in shipments:
        route = shipment["globalRoute"]

        # First stop should be completed (picked up)
        first_stop = route[0]
        if first_stop["state"] != "COMPLETED":
            continue

        # Last stop should be open (not delivered)
        last_stop = route[-1]
        if last_stop["state"] != "OPEN":
            continue

        # Check deduplication (once per day)
        today = datetime.now().strftime("%Y-%m-%d")
        cache_key = f"motus:in_transit:{shipment['id']}:{today}"

        if not redis_client.get(cache_key):
            in_transit.append(shipment)

    # Send webhooks
    for shipment in in_transit:
        payload = transform_turvo_shipment(shipment)
        await send_webhook(MOTUS_IN_TRANSIT_WEBHOOK_URL, payload)

        redis_client.set(cache_key, "1", ex=86400 * 2)  # 2 day TTL

    return {"success": True, "calls_scheduled": len(in_transit)}
```

---

### Phase 6: Optional - Find Load API

**Create `find_load.py`** (on-demand shipment lookup)

**Purpose:** Allow HappyRobot to query specific shipments by ID

```python
@router.get("/find-load")
async def find_load(
    shipment_id: Optional[str] = None,
    custom_id: Optional[str] = None,  # Load number
    status: Optional[str] = None
):
    token = await turvo_client.get_access_token()

    params = {}
    if shipment_id:
        params["id[eq]"] = shipment_id
    if custom_id:
        params["customId[eq]"] = custom_id
    if status:
        params["status[eq]"] = status

    shipments = await turvo_client.list_shipments(params)

    if not shipments:
        raise HTTPException(status_code=404, detail="Shipment not found")

    return transform_turvo_shipment(shipments[0])
```

---

### Phase 7: Deployment

1. **Create Railway Configuration** (`railway.json`)
   ```json
   {
     "build": {
       "builder": "DOCKERFILE",
       "dockerfilePath": "../Dockerfile"
     },
     "deploy": {
       "startCommand": "cd integrations/motus_freight && uvicorn server:app --host 0.0.0.0 --port $PORT",
       "healthcheckPath": "/health",
       "restartPolicyType": "ON_FAILURE",
       "restartPolicyMaxRetries": 10
     }
   }
   ```

2. **Update Dockerfile** (or create separate one)
   ```dockerfile
   FROM python:3.11-slim

   WORKDIR /app
   COPY integrations/motus_freight/requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt

   COPY integrations/motus_freight/ .

   EXPOSE 8000
   CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
   ```

3. **Create Railway Service**
   - New service: `motus-in-transit`
   - Environment variables from `.env`
   - Separate from Peach State deployment

4. **Setup Cron Jobs** (via Railway Cron or external scheduler)
   - Pre-Delivery: `*/15 * * * *` (every 15 minutes)
   - In-Transit: `0 14,19 * * *` (9 AM & 2 PM Central = 14:00, 19:00 UTC)

---

## Key Differences: McLeod vs Turvo

| Aspect | McLeod (Peach State) | Turvo (Motus) |
|--------|---------------------|---------------|
| **Authentication** | Bearer token (static) | OAuth2 (refresh tokens) |
| **Timestamp Format** | `YYYYMMDDHHMMSS-TZ` | ISO 8601 `YYYY-MM-DDTHH:MM:SSZ` |
| **Status Field** | `brokerage_status` (string) | `status.code.value` (integer) |
| **Status Values** | COVERED, BOOKED, TRANSIT | 2105 (En Route), 2115 (Picked Up), etc. |
| **Stop Structure** | Flat `stops[]` array | Nested `globalRoute[]` |
| **ETA Field** | `sched_arrive_early` (scheduled) | `etaToStop.etaValue` (real-time) |
| **Driver Phone** | `movement.override_drvr_cell` | `carrierOrder[0].drivers[0].phone.number` |
| **Miles Remaining** | Not available | `etaToStop.nextStopMiles` |
| **Call Timing** | Pre-PICKUP (1-2 hours before) | Pre-DELIVERY (3 hours before) |

---

## Success Criteria

### Phase 1 (Testing) - Complete When:
- [ ] Turvo authentication working
- [ ] Can query shipments by status
- [ ] Can filter by delivery date
- [ ] ETA and miles data available
- [ ] Driver phone numbers accessible
- [ ] Sample responses documented

### Phase 2-3 (Infrastructure) - Complete When:
- [ ] Project structure created
- [ ] Turvo API client implemented with token refresh
- [ ] Data transformation functions working
- [ ] Unit tests for transformations pass

### Phase 4-5 (Handlers) - Complete When:
- [ ] Pre-delivery handler queries correct shipments
- [ ] Calls triggered 3 hours before delivery
- [ ] In-transit handler runs 2x daily
- [ ] Deduplication prevents duplicate calls
- [ ] Webhooks successfully reach HappyRobot

### Phase 6-7 (Deployment) - Complete When:
- [ ] Railway deployment successful
- [ ] Health checks passing
- [ ] Cron jobs executing on schedule
- [ ] First successful automated call made
- [ ] Monitoring/alerting configured

---

## Risk Mitigation

### Risk 1: Turvo API Limitations
**Mitigation:** Complete Phase 1 thoroughly before building. Document any missing fields and work with Motus to get access or find workarounds.

### Risk 2: Rate Limiting
**Mitigation:** Implement exponential backoff, cache responses, respect Turvo's rate limits. Consider pagination for large result sets.

### Risk 3: Token Expiration
**Mitigation:** Implement robust token refresh logic with retry. Cache tokens with TTL slightly shorter than actual expiration.

### Risk 4: Breaking Peach State Production
**Mitigation:** Keep integrations completely separate. No shared code initially. Deploy to different Railway services.

### Risk 5: Duplicate Calls
**Mitigation:** Redis deduplication with appropriate TTLs. Use shipment ID + date as cache key for in-transit. Test thoroughly in staging.

### Risk 6: Missing Driver Phone Numbers
**Mitigation:** Fallback to carrier dispatch phone. Log when phone unavailable for manual follow-up.

---

## Timeline (Rough Estimates)

| Phase | Tasks | Estimated Effort |
|-------|-------|-----------------|
| 1. API Testing | Test scripts, documentation | 1-2 days |
| 2. Infrastructure | Project setup, client, models | 2-3 days |
| 3. Transformation | Data mapping, utilities | 1-2 days |
| 4. Pre-Delivery | Handler implementation | 1-2 days |
| 5. In-Transit | Handler implementation | 1 day |
| 6. Find Load | Optional on-demand API | 1 day |
| 7. Deployment | Railway setup, testing | 1-2 days |
| **Total** | | **8-13 days** |

*Note: Timeline assumes Turvo API works as expected from testing phase.*

---

## Next Steps

1. **RUN API TESTS** - Execute `turvo_api_test.py` to verify Turvo API
2. **Review findings** - Check if all required data is available
3. **Get approval** - Confirm approach with Motus Freight
4. **Begin implementation** - Start Phase 2 if tests pass

---

## Questions to Answer During Testing

1. Does Turvo provide real-time ETA or just scheduled times?
2. Are driver phone numbers always populated?
3. What's the token expiration time?
4. Are there rate limits on API calls?
5. Can we filter by multiple statuses in one query?
6. Do we get miles remaining for all shipments?
7. How many shipments typically match "En Route + Delivery in 24h"?
8. Are there webhook options from Turvo (push vs pull)?

---

## Reference: Turvo Status Codes

Based on the artifact provided:

- **2101** - Tendered
- **2102** - Covered
- **2105** - En Route ✅ (Primary status to monitor)
- **2115** - Picked Up

(Need to verify complete list during testing)

---

## Contact & Support

- **Turvo API Docs:** [Verify URL]
- **Turvo Support:** [Get contact]
- **Motus Freight Contact:** [Customer contact]
- **HappyRobot Webhook Docs:** [Internal docs]

---

*Last Updated: 2026-01-02*
*Status: Phase 1 - API Testing*
