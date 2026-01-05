"""
Show what the batch payload looks like
"""

import sys
import os
import json
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv("../../.env")

from handlers import turvo_client, turvo_utils

# Get two shipments
shipment_ids = [111580434, 111496723]  # M291186, M290731

shipments_data = []

for sid in shipment_ids:
    print(f"Fetching {sid}...")
    details = turvo_client.get_shipment_details(sid)
    payload = turvo_utils.transform_shipment_for_webhook(details)
    shipments_data.append(payload)

# Create batch payload
batch_payload = {
    "shipments": shipments_data,
    "total_calls": len(shipments_data),
    "timestamp": datetime.now(timezone.utc).isoformat()
}

print("\n" + "="*80)
print("BATCH WEBHOOK PAYLOAD (2 shipments)")
print("="*80)
print(json.dumps(batch_payload, indent=2))
print("="*80)
