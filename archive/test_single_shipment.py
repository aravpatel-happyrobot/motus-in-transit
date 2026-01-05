"""
Quick test to fetch a single shipment's full details
"""

import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

# Get credentials
TURVO_BASE_URL = os.getenv("TURVO_BASE_URL", "https://publicapi.turvo.com/v1")
TURVO_API_KEY = os.getenv("TURVO_API_KEY")
TURVO_USERNAME = os.getenv("TURVO_USERNAME")
TURVO_PASSWORD = os.getenv("TURVO_PASSWORD")

# Step 1: Authenticate
print("Authenticating...")
auth_url = f"{TURVO_BASE_URL}/oauth/token"
auth_payload = {
    "grant_type": "password",
    "username": TURVO_USERNAME,
    "password": TURVO_PASSWORD,
    "client_id": "publicapi",
    "client_secret": "secret",
    "scope": "read+trust+write",
    "type": "business"
}
auth_headers = {
    "Content-Type": "application/json",
    "x-api-key": TURVO_API_KEY
}

auth_response = requests.post(auth_url, headers=auth_headers, json=auth_payload)
token = auth_response.json()["access_token"]
print(f"✓ Got token: {token[:30]}...")

# Step 2: Try different endpoints to get full shipment details
headers = {
    "Authorization": f"Bearer {token}",
    "x-api-key": TURVO_API_KEY,
    "Content-Type": "application/json"
}

# Test shipment ID from previous response
shipment_id = 111537234
custom_id = "M290969"

print(f"\n{'='*80}")
print(f"Testing endpoints for Shipment ID: {shipment_id} (Load: {custom_id})")
print(f"{'='*80}\n")

# Test 1: Get by ID endpoint
print("TEST 1: GET /shipments/{id}")
url1 = f"{TURVO_BASE_URL}/shipments/{shipment_id}"
print(f"URL: {url1}")
response1 = requests.get(url1, headers=headers)
print(f"Status: {response1.status_code}")
if response1.status_code == 200:
    data1 = response1.json()
    with open("turvo_test_responses/shipment_by_id.json", "w") as f:
        json.dump(data1, f, indent=2)
    print("✓ Success! Saved to: shipment_by_id.json")
    print(f"Keys in response: {list(data1.keys())}")
    if "globalRoute" in data1:
        print("✓ Has globalRoute!")
    if "carrierOrder" in data1:
        print("✓ Has carrierOrder!")
else:
    print(f"✗ Failed: {response1.text[:200]}")

# Test 2: List with expand parameters
print(f"\n{'='*80}")
print("TEST 2: GET /shipments/list with expand parameters")
url2 = f"{TURVO_BASE_URL}/shipments/list"
params2 = {
    "id[eq]": shipment_id,
    "expand": "globalRoute,carrierOrder,customerOrder"
}
print(f"URL: {url2}")
print(f"Params: {params2}")
response2 = requests.get(url2, headers=headers, params=params2)
print(f"Status: {response2.status_code}")
if response2.status_code == 200:
    data2 = response2.json()
    with open("turvo_test_responses/shipment_list_expanded.json", "w") as f:
        json.dump(data2, f, indent=2)
    print("✓ Success! Saved to: shipment_list_expanded.json")
    shipments = data2.get("details", {}).get("shipments", [])
    if shipments:
        print(f"Keys in shipment: {list(shipments[0].keys())}")
        if "globalRoute" in shipments[0]:
            print("✓ Has globalRoute!")
            print(f"  Number of stops: {len(shipments[0]['globalRoute'])}")
        if "carrierOrder" in shipments[0]:
            print("✓ Has carrierOrder!")
else:
    print(f"✗ Failed: {response2.text[:200]}")

# Test 3: Search with includeFields
print(f"\n{'='*80}")
print("TEST 3: GET /shipments/list with includeFields")
url3 = f"{TURVO_BASE_URL}/shipments/list"
params3 = {
    "id[eq]": shipment_id,
    "includeFields": "globalRoute,carrierOrder,customerOrder,status"
}
print(f"URL: {url3}")
print(f"Params: {params3}")
response3 = requests.get(url3, headers=headers, params=params3)
print(f"Status: {response3.status_code}")
if response3.status_code == 200:
    data3 = response3.json()
    with open("turvo_test_responses/shipment_list_includefields.json", "w") as f:
        json.dump(data3, f, indent=2)
    print("✓ Success! Saved to: shipment_list_includefields.json")
    shipments = data3.get("details", {}).get("shipments", [])
    if shipments:
        print(f"Keys in shipment: {list(shipments[0].keys())}")
        if "globalRoute" in shipments[0]:
            print("✓ Has globalRoute!")
else:
    print(f"✗ Failed: {response3.text[:200]}")

print(f"\n{'='*80}")
print("All tests complete! Check turvo_test_responses/ for full responses")
print(f"{'='*80}")
