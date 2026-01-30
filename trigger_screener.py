
import requests
import time

try:
    print("Triggering JP Screener...")
    resp = requests.post("http://localhost:5001/api/jp/jongga-v2/run")
    print(f"Status: {resp.status_code}")
    print(resp.json())
except Exception as e:
    print(f"Error: {e}")
