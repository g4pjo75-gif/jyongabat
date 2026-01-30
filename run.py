#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KR Market - Quick Start Entry Point
바로 실행 가능한 메인 스크립트
"""

import os
import sys
import asyncio

# 현재 디렉토리를 패키지 루트로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
os.chdir(BASE_DIR)


def print_banner():
    print("""
╔══════════════════════════════════════════════════════════════╗
║               KR Market - Smart Money Screener               ║
║                   외인/기관 수급 분석 시스템                   ║
╚══════════════════════════════════════════════════════════════╝
    """)


def main():
    print_banner()
    
    print("사용 가능한 기능:")
    print("-" * 60)
    print("1. 종가베팅 V2        - 고급 시그널 생성 (LLM 분석)")
    print("2. VCP 스크리너       - 변동성 수축 패턴 종목 발굴")
    print("3. Market Gate        - 시장 상태 분석")
    print("4. 챗봇 테스트        - AI 챗봇 대화")
    print("5. Flask 서버         - API 서버 실행")
    print("6. 스케줄러 실행      - 자동 데이터 업데이트")
    print("-" * 60)
    
    choice = input("\n실행할 기능 번호를 입력하세요 (1-6): ").strip()
    
    if choice == "1":
        print("\n🎯 종가베팅 V2 실행...")
        from engine.generator import run_screener
        result = asyncio.run(run_screener(capital=50_000_000))
        print(f"\n✅ 완료! {result.filtered_count}개 시그널 생성됨")
        print(f"처리 시간: {result.processing_time_ms:.0f}ms")
        
    elif choice == "2":
        print("\n📊 VCP 스크리너 실행...")
        try:
            from screener import SmartMoneyScreener
            screener = SmartMoneyScreener()
            results = screener.run_screening(max_stocks=50)
            print(f"\n✅ 스크리닝 완료! {len(results)}개 종목 분석됨")
            if hasattr(results, 'head'):
                print(results.head(10).to_string())
        except ImportError:
            print("❌ screener.py가 설치되지 않았습니다.")
        
    elif choice == "3":
        print("\n📈 Market Gate 분석...")
        from market_gate import run_kr_market_gate
        result = run_kr_market_gate()
        print(f"\n시장 상태: {result.get('gate', 'N/A')}")
        print(f"점수: {result.get('score', 0)}")
        print(f"KOSPI: {result.get('kospi_close', 0):,.0f}")
        print(f"KOSDAQ: {result.get('kosdaq_close', 0):,.0f}")
        
    elif choice == "4":
        print("\n🤖 챗봇 테스트 시작...")
        from chatbot import KRStockChatbot
        
        bot = KRStockChatbot("test_user")
        print(bot.get_welcome())
        print("\n(종료하려면 'exit' 입력)")
        
        while True:
            user_input = input("\n👤 You: ").strip()
            if user_input.lower() in ['exit', 'quit', '종료']:
                print("👋 안녕히 가세요!")
                break
            
            response = bot.chat(user_input)
            print(f"\n🤖 Bot: {response}")
        
    elif choice == "5":
        print("\n🚀 Flask 서버 시작...")
        from flask_app import app
        app.run(host='0.0.0.0', port=5001, debug=True)
        
    elif choice == "6":
        print("\n⏰ 스케줄러 실행...")
        try:
            from scheduler import main as scheduler_main
            scheduler_main()
        except ImportError:
            print("❌ scheduler.py가 설치되지 않았습니다.")
        
    else:
        print("잘못된 선택입니다.")
        
    input("\n아무 키나 눌러 종료...")


if __name__ == "__main__":
    main()
