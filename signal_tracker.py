#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Signal Tracker - VCP 시그널 추적 및 로깅
"""

import os
import csv
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict, field


@dataclass
class Signal:
    """시그널 데이터"""
    ticker: str
    name: str
    signal_date: str
    entry_price: float
    status: str = "OPEN"  # OPEN, CLOSED, EXPIRED
    score: float = 0.0
    contraction_ratio: float = 0.0
    foreign_5d: int = 0
    inst_5d: int = 0
    market: str = "KOSPI"
    current_price: float = 0.0
    return_pct: float = 0.0
    exit_date: Optional[str] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)


class SignalTracker:
    """시그널 추적 관리자"""
    
    def __init__(self, data_dir: str = None):
        self.data_dir = data_dir or os.path.join(os.path.dirname(__file__), 'data')
        os.makedirs(self.data_dir, exist_ok=True)
        
        self.signals_file = os.path.join(self.data_dir, 'signals_log.csv')
        self.history_file = os.path.join(self.data_dir, 'signals_history.json')
        
        self.signals: List[Signal] = []
        self._load_signals()
    
    def _load_signals(self):
        """시그널 파일 로드"""
        if not os.path.exists(self.signals_file):
            return
        
        try:
            with open(self.signals_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    signal = Signal(
                        ticker=row.get('ticker', ''),
                        name=row.get('name', ''),
                        signal_date=row.get('signal_date', ''),
                        entry_price=float(row.get('entry_price', 0)),
                        status=row.get('status', 'OPEN'),
                        score=float(row.get('score', 0)),
                        contraction_ratio=float(row.get('contraction_ratio', 0)),
                        foreign_5d=int(row.get('foreign_5d', 0)),
                        inst_5d=int(row.get('inst_5d', 0)),
                        market=row.get('market', 'KOSPI'),
                        current_price=float(row.get('current_price', 0)),
                        return_pct=float(row.get('return_pct', 0))
                    )
                    self.signals.append(signal)
                    
            print(f"✅ {len(self.signals)}개 시그널 로드됨")
            
        except Exception as e:
            print(f"❌ 시그널 로드 실패: {e}")
    
    def save_signals(self):
        """시그널 파일 저장"""
        if not self.signals:
            return
        
        try:
            fieldnames = [
                'ticker', 'name', 'signal_date', 'entry_price', 'status',
                'score', 'contraction_ratio', 'foreign_5d', 'inst_5d',
                'market', 'current_price', 'return_pct', 'exit_date',
                'exit_price', 'exit_reason'
            ]
            
            with open(self.signals_file, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for signal in self.signals:
                    writer.writerow(signal.to_dict())
            
            print(f"✅ {len(self.signals)}개 시그널 저장됨")
            
        except Exception as e:
            print(f"❌ 시그널 저장 실패: {e}")
    
    def add_signal(self, signal: Signal) -> bool:
        """시그널 추가"""
        # 중복 체크
        for existing in self.signals:
            if existing.ticker == signal.ticker and existing.status == "OPEN":
                print(f"⚠️ 이미 열린 시그널 존재: {signal.ticker}")
                return False
        
        self.signals.append(signal)
        self.save_signals()
        print(f"✅ 시그널 추가됨: {signal.name} ({signal.ticker})")
        return True
    
    def close_signal(
        self,
        ticker: str,
        exit_price: float,
        exit_reason: str = "MANUAL"
    ) -> bool:
        """시그널 청산"""
        for signal in self.signals:
            if signal.ticker == ticker and signal.status == "OPEN":
                signal.status = "CLOSED"
                signal.exit_date = datetime.now().strftime('%Y-%m-%d')
                signal.exit_price = exit_price
                signal.exit_reason = exit_reason
                
                # 수익률 계산
                if signal.entry_price > 0:
                    signal.return_pct = ((exit_price - signal.entry_price) / signal.entry_price) * 100
                
                self.save_signals()
                self._log_to_history(signal)
                
                print(f"✅ 시그널 청산: {signal.name} ({signal.ticker}) - {signal.return_pct:.2f}%")
                return True
        
        print(f"⚠️ 열린 시그널 없음: {ticker}")
        return False
    
    def _log_to_history(self, signal: Signal):
        """히스토리에 기록"""
        history = []
        
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            except:
                history = []
        
        history.append(signal.to_dict())
        
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    
    def update_prices(self) -> int:
        """가격 업데이트"""
        from pykrx import stock
        
        today = datetime.now().strftime("%Y%m%d")
        updated_count = 0
        
        for signal in self.signals:
            if signal.status != "OPEN":
                continue
            
            try:
                # 현재가 조회
                ohlcv = stock.get_market_ohlcv(today, today, signal.ticker)
                
                if not ohlcv.empty:
                    current = float(ohlcv.iloc[-1]['종가'])
                    signal.current_price = current
                    
                    if signal.entry_price > 0:
                        signal.return_pct = ((current - signal.entry_price) / signal.entry_price) * 100
                    
                    updated_count += 1
                    print(f"  📈 {signal.name}: {current:,.0f}원 ({signal.return_pct:+.2f}%)")
                    
            except Exception as e:
                continue
        
        if updated_count > 0:
            self.save_signals()
        
        return updated_count
    
    def check_exits(self, stop_loss: float = -5.0, take_profit: float = 15.0) -> List[Signal]:
        """청산 조건 체크"""
        exit_signals = []
        
        for signal in self.signals:
            if signal.status != "OPEN":
                continue
            
            # 손절 체크
            if signal.return_pct <= stop_loss:
                exit_signals.append((signal, "STOP_LOSS"))
            
            # 익절 체크
            elif signal.return_pct >= take_profit:
                exit_signals.append((signal, "TAKE_PROFIT"))
            
            # 시간 청산 체크 (15일)
            signal_date = datetime.strptime(signal.signal_date, '%Y-%m-%d')
            if (datetime.now() - signal_date).days >= 15:
                exit_signals.append((signal, "TIME_EXIT"))
        
        return exit_signals
    
    def get_open_signals(self) -> List[Signal]:
        """열린 시그널 조회"""
        return [s for s in self.signals if s.status == "OPEN"]
    
    def get_stats(self) -> Dict:
        """통계 조회"""
        closed = [s for s in self.signals if s.status == "CLOSED"]
        
        if not closed:
            return {
                "total": len(self.signals),
                "open": len(self.get_open_signals()),
                "closed": 0,
                "win_rate": 0,
                "avg_return": 0
            }
        
        wins = len([s for s in closed if s.return_pct > 0])
        avg_return = sum(s.return_pct for s in closed) / len(closed)
        
        return {
            "total": len(self.signals),
            "open": len(self.get_open_signals()),
            "closed": len(closed),
            "wins": wins,
            "losses": len(closed) - wins,
            "win_rate": (wins / len(closed)) * 100 if closed else 0,
            "avg_return": avg_return,
            "total_return": sum(s.return_pct for s in closed)
        }
    
    def run_daily_update(self):
        """일일 업데이트 실행"""
        print("\n" + "="*50)
        print(f"🔄 일일 시그널 업데이트 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print("="*50)
        
        # 1. 가격 업데이트
        print("\n[1/3] 가격 업데이트...")
        updated = self.update_prices()
        print(f"  → {updated}개 종목 업데이트됨")
        
        # 2. 청산 조건 체크
        print("\n[2/3] 청산 조건 체크...")
        exits = self.check_exits()
        for signal, reason in exits:
            print(f"  ⚠️ {signal.name}: {reason} ({signal.return_pct:.2f}%)")
        
        # 3. 통계 출력
        print("\n[3/3] 현재 통계...")
        stats = self.get_stats()
        print(f"  열린 시그널: {stats['open']}개")
        print(f"  청산 시그널: {stats['closed']}개")
        print(f"  승률: {stats['win_rate']:.1f}%")
        print(f"  평균 수익률: {stats['avg_return']:.2f}%")
        
        print("\n" + "="*50 + "\n")
        
        return stats


# 테스트용
if __name__ == "__main__":
    tracker = SignalTracker()
    
    # 일일 업데이트
    tracker.run_daily_update()
    
    # 열린 시그널 출력
    open_signals = tracker.get_open_signals()
    print(f"\n📊 열린 시그널: {len(open_signals)}개")
    
    for signal in open_signals:
        print(f"  - {signal.name} ({signal.ticker}): {signal.return_pct:+.2f}%")
