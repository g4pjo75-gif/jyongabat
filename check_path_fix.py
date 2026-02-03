import sys
import os

# 사용자 패키지 경로 추정 (경고 메시지 기반)
user_site_packages = r'C:\Users\wawoo\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\LocalCache\local-packages\Python313\site-packages'

if os.path.exists(user_site_packages):
    print(f"Found user site-packages: {user_site_packages}")
    sys.path.append(user_site_packages)
else:
    print(f"User site-packages NOT found at: {user_site_packages}")

try:
    import flask
    print(f"Success! Flask version: {flask.__version__}")
    print(f"Flask path: {flask.__file__}")
except ImportError as e:
    print(f"Error importing flask: {e}")
    # 현재 sys.path 출력
    print("Current sys.path:")
    for p in sys.path:
        print(p)
