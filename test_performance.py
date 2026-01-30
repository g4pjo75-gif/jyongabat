
import requests
import json
import time

url = "http://localhost:5001/api/kr/performance/analyze"
# Find a valid date first? Let's try 2026-01-20 or similar if available, or just a hardcoded one.
# I'll try to list dates first if possible, but let's assume 2026-01-25 exists as per previous context.
payload = {"date": "2026-01-25"} 

print(f"Fetching {url} with payload {payload}...")
start = time.time()
try:
    response = requests.post(url, json=payload, timeout=60)
    elapsed = time.time() - start
    print(f"Elapsed: {elapsed:.2f}s")
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Dates: {data.get('dates')}")
        rows = data.get('rows', [])
        print(f"Rows count: {len(rows)}")
        if rows:
            print(f"First Row: {rows[0]['signal_info']['stock_name']}")
            print(f"First Row Stats: {rows[0]['daily_stats']}")
    else:
        print(f"Error Response: {response.text}")
except Exception as e:
    print(f"Exception: {e}")
