
import requests
import json
import time

url = "http://localhost:5001/api/kr/realtime-prices"
payload = {"tickers": ["005930", "000660", "003380"]} # Samsung, SK Hynix, Harim

print(f"Fetching {url} with payload {payload}...")
start = time.time()
try:
    response = requests.post(url, json=payload, timeout=30)
    elapsed = time.time() - start
    print(f"Elapsed: {elapsed:.2f}s")
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Response data: {data}")
    else:
        print(f"Error Response: {response.text}")
except Exception as e:
    print(f"Exception: {e}")
