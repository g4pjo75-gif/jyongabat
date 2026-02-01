#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask 애플리케이션 진입점
종가베팅 V2 API 서버
"""

import os
import sys
import io

# Windows 콘솔 인코딩 문제 해결 (cp932/cp949 -> UTF-8)
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 현재 디렉토리를 패키지 루트로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
os.chdir(BASE_DIR)

from app import create_app

# Create the Flask app
app = create_app()

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("  Closing Bet V2 API Server Starting")
    print("   http://localhost:5001")
    print("=" * 60 + "\n")
    
    port = int(os.environ.get('FLASK_PORT', 5001))
    debug = os.environ.get('FLASK_DEBUG', 'true').lower() == 'true'
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug,
        use_reloader=False
    )
