
import requests
import json

try:
    url = "http://localhost:5001/api/jp/jongga-v2/latest"
    print(f"Checking {url}...")
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        print("Keys:", data.keys())
        if 'total_scanned' in data:
            print(f"total_scanned: {data['total_scanned']}")
        else:
            print("total_scanned field NOT FOUND")
            
        if 'signals' in data:
            print(f"Signals count: {len(data['signals'])}")
    else:
        print(f"Error: {response.status_code}")
        print(response.text)

except Exception as e:
    print(f"Exception: {e}")
