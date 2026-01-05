# Motus Freight In-Transit Automation

Automated driver check-in calls for Motus Freight using Turvo TMS integration.

## Overview

This system polls the Turvo API every 15 minutes to find loads that are within 4 hours of delivery and triggers automated calls to drivers for real-time ETA updates.

## Features

- ✅ **Real-time ETA tracking** from Turvo GPS data
- ✅ **Temperature monitoring** for refrigerated loads
- ✅ **Smart deduplication** (no repeat calls)
- ✅ **Token caching** (efficient 12-hour OAuth tokens)
- ✅ **Rich context** (notes, equipment, locations)

## Quick Start

### 1. Install Dependencies

```bash
cd integrations/motus_freight
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and configure:

```bash
# Required
TURVO_USERNAME=your_username
TURVO_PASSWORD=your_password
REDIS_URL=redis://...
MOTUS_IN_TRANSIT_WEBHOOK_URL=https://workflows.platform.happyrobot.ai/hooks/...

# Optional
CALL_HOURS_THRESHOLD=4    # Hours before delivery to call
REDIS_TTL_DAYS=30        # Days to remember calls
```

### 3. Run Locally

```bash
cd integrations/motus_freight
uvicorn server:app --reload
```

Visit http://localhost:8000

### 4. Test the Integration

```bash
python test_integration.py
```

## How It Works

```
Every 15 minutes:
  1. Query Turvo for all "En Route" shipments
  2. Get full details (ETA, driver phone, equipment)
  3. Filter: Keep only loads ≤ 4 hours from delivery
  4. Check Redis: Skip if already called
  5. Send webhook to HappyRobot → Trigger call
  6. Mark in Redis (no repeats)
```

## Webhook Payload

Data sent to HappyRobot for each call:

```json
{
  "load_number": "M290638",
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
      "city": "New Oxford",
      "state": "PA"
    }
  },
  "equipment": {
    "type": "Refrigerated",
    "temperature": 34,
    "temp_units": "°F"
  },
  "notes": {
    "pickup": "TEAM DRIVERS ONLY!!!",
    "delivery": "Ships 7-1 PM Strict cut off..."
  }
}
```

## Project Structure

```
motus-in-transit/
├── .env                           # Configuration
├── README.md                      # This file
│
├── integrations/motus_freight/    # Main integration
│   ├── server.py                  # FastAPI app
│   ├── requirements.txt           # Dependencies
│   ├── railway.json              # Deployment config
│   ├── README.md                 # Detailed docs
│   └── handlers/
│       ├── turvo_client.py       # Turvo API wrapper
│       ├── turvo_utils.py        # Data transformation
│       └── in_transit.py         # Main sync logic
│
├── docs/                          # Documentation
│   ├── TECHNICAL_DEEP_DIVE.md    # How it works
│   ├── WEBHOOK_PAYLOAD_SPEC.md   # Payload reference
│   ├── TOKEN_CACHING_STRATEGY.md # Token caching
│   └── ...
│
└── archive/                       # Test scripts
    ├── turvo_api_test.py
    └── ...
```

## Deployment

### Railway (Recommended)

1. Push to GitHub
2. Create Railway service
3. Link repo
4. Set environment variables
5. Deploy

### Cron Setup

Schedule the sync endpoint:

```bash
*/15 * * * * curl -X POST https://your-app.railway.app/sync-in-transit
```

## API Endpoints

- `GET /` - Service info
- `GET /health` - Health check
- `POST /sync-in-transit` - Run in-transit sync

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `CALL_HOURS_THRESHOLD` | Hours before delivery to call | 4 |
| `REDIS_TTL_DAYS` | Days to remember calls | 30 |
| `TURVO_BASE_URL` | Turvo API base URL | https://publicapi.turvo.com/v1 |

## Documentation

- **[Integration README](integrations/motus_freight/README.md)** - Detailed integration docs
- **[Technical Deep Dive](docs/TECHNICAL_DEEP_DIVE.md)** - How everything works
- **[Webhook Payload Spec](docs/WEBHOOK_PAYLOAD_SPEC.md)** - Complete payload reference
- **[Token Caching Strategy](docs/TOKEN_CACHING_STRATEGY.md)** - OAuth2 token management

## Monitoring

Check logs for:
- ✓ Shipments found
- ✓ Calls triggered
- ✗ API errors
- ⚠ Missing data

## Support

For issues:
1. Check Railway logs
2. Test individual components
3. Review documentation
4. Verify environment variables

---

**Status:** Production Ready
**Version:** 1.0.0
**Last Updated:** 2026-01-02
