import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

# Get token
url = "https://publicapi.turvo.com/v1/oauth/token"
headers = {"Content-Type": "application/json", "x-api-key": os.getenv("TURVO_API_KEY")}
payload = {
    "grant_type": "password",
    "username": os.getenv("TURVO_USERNAME"),
    "password": os.getenv("TURVO_PASSWORD"),
    "client_id": "publicapi",
    "client_secret": "secret",
    "scope": "read+trust+write",
    "type": "business"
}
response = requests.post(url, headers=headers, json=payload)
token = response.json()["access_token"]

# Get shipment for Fresh Express (likely reefer) - ID 111484893
shipment_id = 111484893

headers = {
    "Authorization": f"Bearer {token}",
    "x-api-key": os.getenv("TURVO_API_KEY")
}

response = requests.get(f"https://publicapi.turvo.com/v1/shipments/{shipment_id}", headers=headers)
shipment = response.json()["details"]

print("=== CUSTOMER ===")
customer_orders = shipment.get("customerOrder", [])
if customer_orders:
    customer = customer_orders[0].get('customer', {})
    print(f"Customer: {customer.get('name')}")

print("\n=== EQUIPMENT ===")
equipment = shipment.get("equipment", [])
if equipment:
    print(json.dumps(equipment[0], indent=2))

print("\n=== ITEMS/COMMODITIES ===")
items = shipment.get("items", [])
if items:
    for idx, item in enumerate(items[:2]):
        print(f"\nItem {idx+1}:")
        print(json.dumps(item, indent=2))
else:
    print("No items found")

# Save for analysis
with open("turvo_test_responses/reefer_shipment.json", "w") as f:
    json.dump(shipment, f, indent=2)
print("\n✓ Full response saved to: turvo_test_responses/reefer_shipment.json")
