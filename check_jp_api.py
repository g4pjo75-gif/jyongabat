
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
            if 'generated_at' in data:
                print(f"Generated At: {data['generated_at']}")
            if 'total_scanned' in data:
                print(f"Total Scanned: {data['total_scanned']}")
            if 'signals' in data:
                print(f"Signals count: {len(data['signals'])}")
        else:
            print(f"Error: {response.text[:200]}")
    except Exception as e:
        print(f"Exception: {e}")

base_url = "http://localhost:5001/api/jp"
print("--- Check N225 ---")
check_endpoint(f"{base_url}/jongga-v2/latest?type=n225")
print("\n--- Check N400 ---")
check_endpoint(f"{base_url}/jongga-v2/latest?type=n400")
