#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KR Market Scheduler - 백그라운드 데이터 업데이트 스케줄러
"""

import os
import sys
import time
import json
import asyncio
import argparse
from datetime import datetime, timedelta
from typing import Optional
import threading


# 경로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)


class MarketScheduler:
    """시장 데이터 업데이트 스케줄러"""
    
    def __init__(self):
        self.data_dir = os.path.join(BASE_DIR, 'data')
        os.makedirs(self.data_dir, exist_ok=True)
        
        self.is_running = False
        self.last_update = None
        
    def run_vcp_scan(self) -> dict:
        """VCP 스캔 실행"""
        print("🔍 [VCP] 스캔 시작...")
        
        try:
            from screener import SmartMoneyScreener
            
            screener = SmartMoneyScreener()
            results = screener.run_screening(max_stocks=50)
            
            if results.empty:
                return {"status": "no_data", "count": 0}
            
            signals = screener.generate_signals(results)
            
            # signals_log.csv 저장
            signals_path = os.path.join(self.data_dir, 'signals_log.csv')
            results.to_csv(signals_path, index=False, encoding='utf-8-sig')
            
            print(f"✅ [VCP] {len(signals)}개 시그널 저장됨")
            
            return {
                "status": "success",
                "count": len(signals),
                "signals": signals[:10]  # 상위 10개만 반환
            }
            
        except Exception as e:
            print(f"❌ [VCP] 스캔 실패: {e}")
            return {"status": "error", "error": str(e)}
    
    def run_jongga_v2(self) -> dict:
        """종가베팅 V2 엔진 실행"""
        print("🎯 [Jongga V2] 엔진 실행 시작...")
        
        try:
            from engine.generator import run_screener
            
            result = asyncio.run(run_screener(capital=50_000_000))
            
            print(f"✅ [Jongga V2] {result.filtered_count}개 시그널 생성됨")
            
            return {
                "status": "success",
                "date": result.date.isoformat(),
                "filtered_count": result.filtered_count,
                "processing_time": result.processing_time_ms
            }
            
        except Exception as e:
            print(f"❌ [Jongga V2] 실행 실패: {e}")
            return {"status": "error", "error": str(e)}
    
    def run_market_gate(self) -> dict:
        """Market Gate 상태 업데이트"""
        print("📈 [Market Gate] 분석 시작...")
        
        try:
            from market_gate import run_kr_market_gate
            
            result = run_kr_market_gate()
            
            # 캐시 저장
            cache_path = os.path.join(self.data_dir, 'market_gate_cache.json')
            with open(cache_path, 'w', encoding='utf-8') as f:
                # to_dict()가 있으면 사용, 없으면 변환
                if hasattr(result, 'to_dict'):
                    data = result.to_dict()
                elif isinstance(result, dict):
                    data = result
                else:
                    data = vars(result)
                    
                data['updated_at'] = datetime.now().isoformat()
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ [Market Gate] 상태: {result.get('gate', 'N/A')}, 점수: {result.get('score', 0)}")
            
            return {
                "status": "success",
                "gate": result.get('gate', 'NEUTRAL'),
                "score": result.get('score', 50)
            }
            
        except Exception as e:
            print(f"❌ [Market Gate] 분석 실패: {e}")
            return {"status": "error", "error": str(e)}
    
    def run_full_update(self) -> dict:
        """전체 데이터 업데이트"""
        print("\n" + "="*60)
        print(f"🚀 전체 업데이트 시작 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60 + "\n")
        
        results = {}
        start_time = time.time()
        
        # 1. Market Gate
        results["market_gate"] = self.run_market_gate()
        
        # 2. VCP Scan
        results["vcp_scan"] = self.run_vcp_scan()
        
        # 3. Jongga V2
        results["jongga_v2"] = self.run_jongga_v2()
        
        elapsed = time.time() - start_time
        
        print("\n" + "="*60)
        print(f"✅ 전체 업데이트 완료 ({elapsed:.1f}초 소요)")
        print("="*60 + "\n")
        
        self.last_update = datetime.now()
        
        return {
            "status": "completed",
            "elapsed_seconds": elapsed,
            "results": results,
            "updated_at": self.last_update.isoformat()
        }
    
    def start_scheduler(self, interval_minutes: int = 30):
        """스케줄러 시작"""
        print(f"\n⏰ 스케줄러 시작 - {interval_minutes}분 간격")
        print("   Ctrl+C로 종료하세요.\n")
        
        self.is_running = True
        
        # 즉시 1회 실행
        self.run_full_update()
        
        while self.is_running:
            try:
                # 대기
                print(f"\n💤 다음 업데이트까지 {interval_minutes}분 대기...\n")
                time.sleep(interval_minutes * 60)
                
                # 거래 시간 체크 (09:00 ~ 15:30)
                now = datetime.now()
                if now.weekday() >= 5:  # 주말
                    print("📅 주말입니다. 업데이트 건너뜀.")
                    continue
                
                if now.hour < 9 or (now.hour == 15 and now.minute > 30) or now.hour >= 16:
                    print("⏰ 장외 시간입니다. 업데이트 건너뜀.")
                    continue
                
                # 업데이트 실행
                self.run_full_update()
                
            except KeyboardInterrupt:
                print("\n\n👋 스케줄러를 종료합니다.")
                self.is_running = False
                break
    
    def stop_scheduler(self):
        """스케줄러 중지"""
        self.is_running = False


def run_vcp_scan() -> dict:
    """VCP 스캔 실행 (Flask 라우트용)"""
    scheduler = MarketScheduler()
    return scheduler.run_vcp_scan()


def run_full_update() -> dict:
    """전체 업데이트 실행 (Flask 라우트용)"""
    scheduler = MarketScheduler()
    return scheduler.run_full_update()


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='KR Market Scheduler')
    parser.add_argument('--now', action='store_true', help='즉시 1회 실행')
    parser.add_argument('--interval', type=int, default=30, help='실행 간격 (분)')
    parser.add_argument('--vcp', action='store_true', help='VCP 스캔만 실행')
    parser.add_argument('--jongga', action='store_true', help='종가베팅 V2만 실행')
    parser.add_argument('--gate', action='store_true', help='Market Gate만 실행')
    
    args = parser.parse_args()
    
    scheduler = MarketScheduler()
    
    if args.vcp:
        result = scheduler.run_vcp_scan()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.jongga:
        result = scheduler.run_jongga_v2()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.gate:
        result = scheduler.run_market_gate()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.now:
        result = scheduler.run_full_update()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        scheduler.start_scheduler(interval_minutes=args.interval)


if __name__ == "__main__":
    main()
