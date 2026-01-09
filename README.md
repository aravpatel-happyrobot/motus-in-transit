# Motus Freight In-Transit Automation

Automated driver check-in calls for Motus Freight using Turvo TMS integration.

## Overview

This system polls the Turvo API to find loads approaching delivery and triggers automated calls to drivers for real-time ETA updates. It uses a **two-window call system**:

- **Window 1 (Check-in):** 3-4 hours before delivery - initial status check
- **Window 2 (Final):** 0-30 minutes before delivery - final confirmation

## Features

- **Two-window call system** - Check-in and final calls at optimal times
- **Real-time ETA tracking** from Turvo GPS data
- **Temperature monitoring** for refrigerated loads
- **Smart deduplication** - Separate tracking per call type (no repeat calls)
- **Token caching** - Efficient 12-hour OAuth tokens via Redis
- **Owner filtering** - Control which shipments trigger calls
- **API authentication** - Bearer token security for the sync endpoint

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and configure:

```bash
# Redis (for token caching and deduplication)
REDIS_URL=redis://...

# Turvo API Configuration
TURVO_BASE_URL=https://publicapi.turvo.com/v1
TURVO_API_KEY=your_api_key
TURVO_USERNAME=your_username
TURVO_PASSWORD=your_password
TURVO_CLIENT_ID=publicapi
TURVO_CLIENT_SECRET=secret

# HappyRobot Webhook
MOTUS_IN_TRANSIT_WEBHOOK_URL=https://workflows.platform.happyrobot.ai/hooks/...

# API Security
API_SECRET_KEY=your_secret_key

# Call Windows
CALL_WINDOW_1_MIN=3      # Window 1: 3-4 hours before delivery
CALL_WINDOW_1_MAX=4
CALL_WINDOW_2_MIN=0      # Window 2: 0-30 minutes before delivery
CALL_WINDOW_2_MAX=0.5
REDIS_TTL_DAYS=2

# Owner Filtering (optional)
ALLOWED_OWNERS=
ALLOWED_OWNER_IDS=
```

### 3. Run Locally

```bash
uvicorn server:app --reload
```

Visit http://localhost:8000

## How It Works

```
Every 5 minutes (during business hours):
  1. Query Turvo for all "En Route" shipments (with pagination)
  2. Get full details for each (ETA, driver phone, equipment)
  3. Filter by call windows:
     - Window 1: 3-4 hours from delivery → "checkin" call
     - Window 2: 0-30 minutes from delivery → "final" call
  4. Check Redis: Skip if already called for this window (2-day TTL)
  5. Send webhook to HappyRobot → Trigger calls
  6. Mark as called in Redis (separate keys per call type)
```

## Webhook Payload

Data sent to HappyRobot for each call:

```json
{
  "call_type": "checkin",
  "load_number": "M290638",
  "driver": {
    "name": "Harrison",
    "phone": "5096552011"
  },
  "delivery": {
    "eta": "2026-01-03T00:06:23Z",
    "eta_formatted": "Jan 2, 19:06 EST",
    "hours_until": 3.5,
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
├── .env                    # Configuration (not committed)
├── .env.example            # Example configuration
├── README.md               # This file
├── railway.json            # Railway deployment config
├── requirements.txt        # Python dependencies
├── server.py               # FastAPI app
├── handlers/
│   ├── __init__.py
│   ├── in_transit.py       # Main sync logic
│   ├── turvo_client.py     # Turvo API wrapper
│   └── turvo_utils.py      # Data transformation
└── docs/
    ├── voice-agent-prompts.md      # Voice agent prompt guide
    ├── email-templates.md          # Post-call email templates
    └── happyrobot-workflow-design.md
```

## Deployment

### Railway

1. Push to GitHub
2. Create Railway service from repo
3. Set environment variables in Railway dashboard
4. Deploy

### Cron Setup

Use Railway's cron service or an external service to trigger the sync endpoint:

**Endpoint:** `POST https://your-app.railway.app/sync-in-transit`

**Headers:**
```
Authorization: Bearer <API_SECRET_KEY>
```

**Recommended Schedule:** Every 5 minutes during business hours (4:30 AM - 5 PM CST)
```
*/5 10-23 * * *   (UTC, which is CST + 6)
```

## API Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/` | GET | No | Service info |
| `/health` | GET | No | Health check |
| `/sync-in-transit` | POST | Yes | Run in-transit sync |

### Authentication

The `/sync-in-transit` endpoint requires a Bearer token:

```bash
curl -X POST https://your-app.railway.app/sync-in-transit \
  -H "Authorization: Bearer YOUR_API_SECRET_KEY"
```

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `CALL_WINDOW_1_MIN` | Window 1 minimum hours before delivery | 3 |
| `CALL_WINDOW_1_MAX` | Window 1 maximum hours before delivery | 4 |
| `CALL_WINDOW_2_MIN` | Window 2 minimum hours before delivery | 0 |
| `CALL_WINDOW_2_MAX` | Window 2 maximum hours before delivery | 0.5 |
| `REDIS_TTL_DAYS` | Days to remember calls | 2 |
| `API_SECRET_KEY` | Bearer token for sync endpoint | (none) |
| `ALLOWED_OWNERS` | Filter by owner names (comma-separated) | "" (all) |
| `ALLOWED_OWNER_IDS` | Filter by owner IDs (comma-separated) | "" (all) |

### Owner Filtering

Control which shipments trigger calls based on who owns them in Turvo:

**By Name:**
```bash
ALLOWED_OWNERS=Cameron Murray,Justin Kinnett
```

**By ID:**
```bash
ALLOWED_OWNER_IDS=201288,5564
```

**Disable filtering (all owners):**
```bash
ALLOWED_OWNERS=
ALLOWED_OWNER_IDS=
```

## Monitoring

Check Railway logs for:
- `✓` Shipments found
- `✓` Calls triggered (checkin/final)
- `✗` API errors
- `⚠` Missing data or filtered loads

---

**Status:** Production Ready
**Version:** 2.0.0
**Last Updated:** 2026-01-09
