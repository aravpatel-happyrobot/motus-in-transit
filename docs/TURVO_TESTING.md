# Turvo API Testing Guide

## Prerequisites

Before running the API tests, you need:

1. **Turvo API Password** - Add to `.env` file
2. **Python 3.11+** installed
3. **Dependencies** installed

## Setup

### 1. Add Turvo Password to .env

Edit `.env` and add your Turvo password:

```bash
TURVO_PASSWORD=your_actual_password_here
```

The other Turvo credentials are already configured:
- API Key: `9CtJ7rMImv6BTB6x922xR6xDN6ckpiTG4FKrvbL1`
- Username: `support@happyrobot.ai`
- Base URL: `https://publicapi.turvo.com/v1`

### 2. Install Dependencies

```bash
pip install requests python-dotenv
```

Or if you prefer using the existing requirements:

```bash
cd integrations/meiborg_brothers
pip install -r requirements.txt
cd ../..
```

## Running the Tests

From the project root directory:

```bash
python turvo_api_test.py
```

## What the Tests Do

The test script runs 5 comprehensive tests:

### Test 1: OAuth2 Authentication
- Verifies credentials work
- Gets access token
- Checks token expiration time
- **Result:** Saves `auth_response.json`

### Test 2: En Route Shipments
- Queries for shipments with status `2105` (En Route)
- Verifies API query works
- **Result:** Saves `en_route_shipments_response.json`

### Test 3: Delivery Date Filtering
- Queries shipments delivering in next 24 hours
- Tests date range filters
- Shows delivery time distribution
- **Result:** Saves `delivery_date_filter_response.json`

### Test 4: Pre-Delivery Call Window
- Simulates pre-delivery automation logic
- Finds loads 2.5-3.5 hours from delivery
- Identifies which loads need calls NOW
- **Result:** Saves `calls_needed_now.json`

### Test 5: In-Transit Identification
- Finds loads that are picked up but not delivered
- Verifies stop state logic works
- **Result:** Saves `in_transit_identification_response.json`

## Test Output

### Terminal Output

The script provides color-coded output:
- ✅ **Green** - Success
- ❌ **Red** - Error
- ⚠️ **Yellow** - Warning
- ℹ️ **Cyan** - Info

### Saved Responses

All API responses are saved to `./turvo_test_responses/`:

```
turvo_test_responses/
├── auth_response.json
├── en_route_shipments_response.json
├── delivery_date_filter_response.json
├── pre_delivery_window_response.json
├── in_transit_identification_response.json
├── calls_needed_now.json
└── structure_analysis.json
```

These files are crucial for:
- Understanding Turvo's data structure
- Debugging field mappings
- Reference during implementation

## Expected Results

### ✅ All Tests Pass

If all 5 tests pass, you should see:

```
FINAL SUMMARY
✓ Authentication: PASSED
✓ En Route Shipments Query: PASSED
✓ Delivery Date Filtering: PASSED
✓ Pre-Delivery Call Logic: PASSED
✓ In-Transit Identification: PASSED

Overall: 5/5 tests passed
🎉 All tests passed! Ready to proceed with implementation.
```

**Next Steps:**
1. Review saved JSON responses
2. Verify all required fields are present
3. Begin Phase 2 (Infrastructure Setup) from implementation plan

### ⚠️ Some Tests Fail

Possible issues:

1. **Authentication Fails**
   - Check `TURVO_PASSWORD` in `.env`
   - Verify username is correct
   - Check if API key is valid

2. **No Shipments Found**
   - Not necessarily an error
   - Might not have any En Route shipments at the moment
   - Try different status codes or date ranges

3. **Missing Fields**
   - Check `structure_analysis.json`
   - Document which fields are unavailable
   - Plan workarounds or alternative data sources

## Critical Fields to Verify

During testing, ensure these fields are available:

### Shipment Level
- ✅ `id` - Shipment ID
- ✅ `customId` - Load number
- ✅ `status.code.value` - Status code (e.g., 2105)

### Stop/Route Level
- ✅ `globalRoute[].stopType.value` - "Pickup" or "Delivery"
- ✅ `globalRoute[].state` - "OPEN", "COMPLETED", etc.
- ✅ `globalRoute[].etaToStop.etaValue` - ETA timestamp
- ✅ `globalRoute[].etaToStop.nextStopMiles` - Miles remaining
- ✅ `globalRoute[].address.city` - Location city
- ✅ `globalRoute[].address.state` - Location state

### Carrier/Driver Level
- ✅ `carrierOrder[0].carrier.name` - Carrier name
- ✅ `carrierOrder[0].drivers[0].context.name` - Driver name
- ✅ `carrierOrder[0].drivers[0].phone.number` - Driver phone

## Troubleshooting

### "TURVO_PASSWORD not set"
```bash
# Add to .env
TURVO_PASSWORD=your_password
```

### "ModuleNotFoundError: No module named 'requests'"
```bash
pip install requests python-dotenv
```

### "Authentication failed: 401"
- Verify credentials are correct
- Check if password has special characters (might need escaping)
- Contact Turvo support if credentials should work

### "No shipments found"
Try querying different statuses:
- `2101` - Tendered
- `2102` - Covered
- `2115` - Picked Up

Or expand the date range:
```python
# In test script, change:
tomorrow = now + timedelta(days=7)  # 7 days instead of 1
```

## Next Steps After Testing

1. **Review Results**
   - Open saved JSON files in `turvo_test_responses/`
   - Verify data structure matches expectations
   - Document any missing or unexpected fields

2. **Answer Key Questions**
   - Are driver phone numbers always populated?
   - Is real-time ETA available or just scheduled times?
   - Are miles remaining accurate?
   - What's the token expiration time?

3. **Update Implementation Plan**
   - Adjust field mappings based on actual data
   - Plan workarounds for missing fields
   - Update `TURVO_IMPLEMENTATION_PLAN.md`

4. **Begin Development**
   - If tests pass, proceed to Phase 2
   - Create `integrations/motus_freight/` directory
   - Start building Turvo client

## Questions or Issues?

If you encounter issues:
1. Check saved error files in `turvo_test_responses/`
2. Review Turvo API documentation
3. Contact Turvo support
4. Document findings for team review

---

**Last Updated:** 2026-01-02
**Status:** Ready for Testing
