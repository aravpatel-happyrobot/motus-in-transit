"""
Test the Motus integration end-to-end
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv("../../.env")

# Now import handlers
from handlers import in_transit

if __name__ == "__main__":
    print("Testing Motus Freight In-Transit Integration")
    print("="*80)

    # Note: This will NOT send actual webhooks unless MOTUS_IN_TRANSIT_WEBHOOK_URL is configured
    webhook_url = os.getenv("MOTUS_IN_TRANSIT_WEBHOOK_URL")

    if not webhook_url or "YOUR_WEBHOOK_ID" in webhook_url:
        print("⚠ Warning: MOTUS_IN_TRANSIT_WEBHOOK_URL not configured")
        print("  Webhooks will fail but you can see the logic working")
        print()

    # Run the sync
    result = in_transit.sync_in_transit()

    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)
    print(f"\nResult: {result}")
