
import requests
import time

def check_endpoint(url):
    print(f"Checking {url}...")
    try:
        response = requests.get(url, timeout=5)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if 'signals' in data:
                print(f"Signals count: {len(data['signals'])}")
            else:
                print("No 'signals' field")
        else:
            print(f"Error Body: {response.text[:200]}")
    except Exception as e:
        print(f"Exception: {e}")

base_url = "http://localhost:5001/api/jp"
check_endpoint(f"{base_url}/jongga-v2/latest?type=n225")
