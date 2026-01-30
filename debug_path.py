
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

try:
    from app.routes.jp_market import get_jp_data_dir
    data_dir = get_jp_data_dir()
    print(f"Resolved Data Dir: {data_dir}")
    print(f"Exists: {os.path.exists(data_dir)}")
    
    # Check specifically for N225 latest file
    n225_file = os.path.join(data_dir, 'jongga_v2_n225_latest.json')
    print(f"N225 File: {n225_file}")
    print(f"File Exists: {os.path.exists(n225_file)}")

except Exception as e:
    print(f"Error: {e}")
