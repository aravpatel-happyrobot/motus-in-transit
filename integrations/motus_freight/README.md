# Motus Freight In-Transit Integration

Turvo TMS integration for automated in-transit driver calls.

## Overview

This integration polls the Turvo API for En Route shipments and triggers automated calls to drivers who are within 4 hours of delivery.

## Features

- ✅ **Real-time ETA tracking** from Turvo
- ✅ **Temperature monitoring** for reefer loads
- ✅ **Token caching** (12-hour OAuth tokens cached in Redis)
- ✅ **Deduplication** (Redis prevents duplicate calls)
- ✅ **Comprehensive data** (notes, equipment, locations)
- ✅ **Scalable** (handles 100+ shipments per poll)

## Architecture

```
Cron (every 15 min)
  ↓
POST /sync-in-transit
  ↓
1. Query Turvo: Get all En Route shipments (status 2105)
  ↓
2. For each shipment:
   - Get full details from /shipments/{id}
   - Extract delivery ETA, driver phone, equipment
   - Calculate hours until delivery
  ↓
3. Filter: Keep only loads ≤ 4 hours from delivery
  ↓
4. Check Redis: Skip if already called
  ↓
5. Send webhook to HappyRobot
  ↓
6. Mark in Redis (no repeats for 30 days)
```

## Installation

### 1. Install Dependencies

```bash
cd integrations/motus_freight
pip install -r requirements.txt
```

### 2. Configure Environment

Edit `.env` in project root:

```bash
# Turvo API
TURVO_BASE_URL=https://publicapi.turvo.com/v1
TURVO_API_KEY=your_api_key
TURVO_USERNAME=your_username
TURVO_PASSWORD=your_password

# Redis (for caching and deduplication)
REDIS_URL=redis://default:password@host:port

# Webhook
MOTUS_IN_TRANSIT_WEBHOOK_URL=https://workflows.platform.happyrobot.ai/hooks/YOUR_WEBHOOK_ID

# Configuration
CALL_HOURS_THRESHOLD=4      # Call if ≤ 4 hours from delivery
REDIS_TTL_DAYS=30           # Remember calls for 30 days
```

### 3. Run Locally

```bash
cd integrations/motus_freight
uvicorn server:app --reload --port 8000
```

Visit: http://localhost:8000

## API Endpoints

### `GET /`
Root endpoint with service info

### `GET /health`
Health check for Railway deployment

### `POST /sync-in-transit`
Main in-transit sync endpoint

**Response:**
```json
{
  "success": true,
  "timestamp": "2026-01-02T22:24:32Z",
  "shipments_total": 24,
  "already_called": 10,
  "skipped": 9,
  "calls_made": 5,
  "errors": []
}
```

## Webhook Payload

Data sent to HappyRobot when triggering a call:

```json
{
  "load_number": "M290638",
  "shipment_id": 111484893,

  "driver": {
    "name": "Harrison",
    "phone": "5096552011"
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
    }
  },

  "pickup": {
    "location": {
      "name": "Fresh Express - Streamwood, IL",
      "city": "Streamwood",
      "state": "IL"
    }
  },

  "equipment": {
    "type": "Refrigerated",
    "size": "53 ft",
    "temperature": 34,
    "temp_units": "°F",
    "weight": 42000,
    "weight_units": "lb",
    "description": "raw produce"
  },

  "notes": {
    "status": "per driver via phone LNR",
    "pickup": "TEAM DRIVERS ONLY!!!",
    "delivery": "Ships 7-1 PM Strict cut off...",
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

  "source": "motus_in_transit",
  "timestamp": "2026-01-02T22:24:32Z"
}
```

**Note:** For non-reefer loads, `temperature` and `temp_units` will be `null`.

## Testing

### Manual Trigger

```bash
curl -X POST http://localhost:8000/sync-in-transit
```

### Test Turvo Connection

```python
from handlers import turvo_client

# Test authentication
token = turvo_client.get_turvo_token()
print(f"Token: {token[:30]}...")

# Test shipment query
shipments = turvo_client.list_shipments(status=2105, page_size=10)
print(f"Found {len(shipments)} En Route shipments")
```

## Deployment

### Railway

1. Create new Railway service
2. Link to GitHub repo
3. Set environment variables from `.env`
4. Deploy

Railway will use `railway.json` for build/deploy configuration.

### Cron Setup

Use Railway Cron or external scheduler:

```
*/15 * * * * curl -X POST https://your-app.railway.app/sync-in-transit
```

Every 15 minutes.

## Monitoring

### Logs

Check Railway logs for:
- ✓ Authentication success
- ✓ Shipments found
- ✓ Calls triggered
- ✗ API errors
- ⚠ Missing data warnings

### Metrics

Key metrics to track:
- Shipments processed per run
- Calls triggered per run
- API response times
- Redis hit rate (token cache)
- Failed webhooks

## Troubleshooting

### No shipments found

**Possible causes:**
- No loads currently En Route (status 2105)
- API credentials invalid
- Network issues

**Check:**
```bash
curl -X GET "https://publicapi.turvo.com/v1/shipments/list?status[eq]=2105&pageSize=10" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "x-api-key: YOUR_API_KEY"
```

### No calls triggered

**Possible causes:**
- All loads > 4 hours from delivery
- All loads already called (check Redis)
- Missing driver phone numbers
- Webhook URL not configured

**Check:**
- Review logs for "skipped" reasons
- Check `MOTUS_IN_TRANSIT_WEBHOOK_URL` is set
- Verify Redis connection

### Authentication fails

**Check:**
- `TURVO_USERNAME` and `TURVO_PASSWORD` are correct
- `TURVO_API_KEY` is valid
- Turvo account is active

### Duplicate calls

**Possible causes:**
- Redis not connected
- Redis keys expired (check TTL)

**Fix:**
- Verify `REDIS_URL` is correct
- Check Redis is running
- Increase `REDIS_TTL_DAYS` if needed

## Configuration

### Call Threshold

Change when to trigger calls:

```bash
CALL_HOURS_THRESHOLD=3  # Call 3 hours before delivery
```

### Deduplication TTL

Change how long to remember calls:

```bash
REDIS_TTL_DAYS=7  # Remember for 7 days
```

## File Structure

```
integrations/motus_freight/
├── server.py                  # FastAPI application
├── requirements.txt           # Python dependencies
├── railway.json              # Railway deployment config
├── README.md                 # This file
└── handlers/
    ├── __init__.py
    ├── turvo_client.py       # Turvo API wrapper
    ├── turvo_utils.py        # Data transformation
    └── in_transit.py         # Main sync logic
```

## Related Documentation

- [TECHNICAL_DEEP_DIVE.md](../../TECHNICAL_DEEP_DIVE.md) - How it works under the hood
- [WEBHOOK_PAYLOAD_SPEC.md](../../WEBHOOK_PAYLOAD_SPEC.md) - Complete payload reference
- [TOKEN_CACHING_STRATEGY.md](../../TOKEN_CACHING_STRATEGY.md) - Token caching details
- [TURVO_IMPLEMENTATION_PLAN.md](../../TURVO_IMPLEMENTATION_PLAN.md) - Implementation plan

## Support

For issues or questions:
1. Check logs in Railway dashboard
2. Review error messages in API response
3. Test individual components (auth, shipments query, etc.)
4. Check Turvo API status

---

**Last Updated:** 2026-01-02
**Version:** 1.0.0
**Status:** Ready for Production
