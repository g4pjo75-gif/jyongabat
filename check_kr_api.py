
import requests
import time

def check_endpoint(url):
    print(f"Checking {url}...")
    start = time.time()
    try:
        response = requests.get(url, timeout=5)
        elapsed = time.time() - start
        print(f"Status: {response.status_code}, Time: {elapsed:.2f}s")
        if response.status_code == 200:
            data = response.json()
            keys = list(data.keys())[:5]
            print(f"Keys: {keys}")
        else:
            print(f"Error: {response.text[:200]}")
    except Exception as e:
        print(f"Exception: {e}")

base_url = "http://localhost:5001/api/kr"
check_endpoint(f"{base_url}/market-gate")
check_endpoint(f"{base_url}/backtest-summary")
check_endpoint(f"{base_url}/signals")
