"""
Show actual webhook payload for one shipment
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv("../../.env")

from handlers import turvo_client, turvo_utils

# Get one of the loads that just triggered
shipment_id = 111579596  # M291180 - BATAVIA, IL

print("Fetching shipment details...")
details = turvo_client.get_shipment_details(shipment_id)

print("\nTransforming to webhook payload...")
payload = turvo_utils.transform_shipment_for_webhook(details)

print("\n" + "="*80)
print("ACTUAL WEBHOOK PAYLOAD")
print("="*80)
print(json.dumps(payload, indent=2))
print("="*80)
