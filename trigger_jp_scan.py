
import requests
import time

BASE_URL = "http://127.0.0.1:5000/api/jp/jongga-v2/run"

def trigger_scan(run_type):
    print(f"Triggering scan for {run_type}...")
    try:
        resp = requests.post(f"{BASE_URL}?type={run_type}")
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.json()}")
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    # Trigger both
    trigger_scan("n225")
    trigger_scan("n400")
    print("Requests sent. Checking status in 5 seconds...")
    time.sleep(5)
    
    # Check status
    try:
        status = requests.get("http://127.0.0.1:5000/api/jp/screener/status").json()
        print("Screener Status:", status)
    except:
        print("Could not check status")
