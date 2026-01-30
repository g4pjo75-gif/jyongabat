import requests
import json
import sys
import time

start = time.time()

url = "http://localhost:5001/api/kr/vcp/history/2026-01-25"

print(f"Fetching {url}...")
try:
    response = requests.get(url, timeout=60)
    elapsed = time.time() - start
    print(f"Elapsed: {elapsed:.2f}s")
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Data keys: {list(data.keys())}")
        if 'signals' in data:
            print(f"Signals count: {len(data['signals'])}")
            if data['signals']:
                sig = data['signals'][0]
                print(f"First signal sample keys: {list(sig.keys())}")
                print(f"Entry Price: {sig.get('entry_price')}")
                print(f"Current Price: {sig.get('current_price')}")
                print(f"Return Pct: {sig.get('return_pct')}")
    else:
        print(f"Error Response: {response.text}")
except Exception as e:
    print(f"Exception: {e}")
