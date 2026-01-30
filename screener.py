#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Smart Money Screener - VCP 패턴 + 외인/기관 수급 스크리너
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class VCPResult:
    """VCP 분석 결과"""
    ticker: str
    name: str
    market: str
    score: float = 0.0
    contraction_ratio: float = 0.0
    foreign_5d: int = 0
    inst_5d: int = 0
    foreign_trend: str = "neutral"
    inst_trend: str = "neutral"
    is_double_buy: bool = False
    supply_demand_score: float = 0.0
    supply_demand_stage: str = "중립"
    current_price: float = 0.0
    change_pct: float = 0.0
    volume: int = 0


class SmartMoneyScreener:
    """
    VCP 패턴 + 외인/기관 수급 기반 스크리너
    
    점수 가중치:
    - 외국인 순매매량 (25점)
    - 외국인 연속 매수일 (15점)
    - 기관 순매매량 (20점)
    - 기관 연속 매수일 (10점)
    - 거래량 대비 비율 (20점)
    - VCP 패턴 (10점)
    """
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.data_dir = os.path.join(os.path.dirname(__file__), 'data')
        
        # 기본 설정
        self.weight_foreign = self.config.get('weight_foreign', 0.40)
        self.weight_inst = self.config.get('weight_inst', 0.30)
        self.weight_technical = self.config.get('weight_technical', 0.20)
        self.weight_vcp = self.config.get('weight_vcp', 0.10)
        
        # VCP 기준
        self.contraction_threshold = self.config.get('contraction_threshold', 0.7)
        
    def run_screening(self, max_stocks: int = 50) -> pd.DataFrame:
        """
        스크리닝 실행
        
        Args:
            max_stocks: 분석할 최대 종목 수
        
        Returns:
            스크리닝 결과 DataFrame
        """
        results = []
        
        # 1. 종목 리스트 로드
        stocks = self._load_stock_list()
        if stocks.empty:
            print("❌ 종목 리스트를 로드할 수 없습니다.")
            return pd.DataFrame()
        
        print(f"📊 {len(stocks)}개 종목 분석 시작...")
        
        # 2. 각 종목 분석 (병렬 처리)
        import concurrent.futures
        
        # 분석 대상 준비
        targets = []
        for idx, row in stocks.head(max_stocks).iterrows():
            ticker = str(row.get('ticker', row.get('code', ''))).zfill(6)
            name = row.get('name', ticker)
            market = row.get('market', 'KOSPI')
            targets.append((ticker, name, market))
            
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_stock = {
                executor.submit(self._analyze_stock, ticker, name, market): (ticker, name)
                for ticker, name, market in targets
            }
            
            for future in concurrent.futures.as_completed(future_to_stock):
                ticker, name = future_to_stock[future]
                try:
                    result = future.result()
                    if result and result.score >= 20: 
                        results.append(result)
                except Exception as e:
                    print(f"Error analyzing {name} ({ticker}): {e}")
                    continue
        
        # 3. 결과 DataFrame 생성
        if not results:
            return pd.DataFrame()
        
        df = pd.DataFrame([vars(r) for r in results])
        df = df.sort_values('score', ascending=False)
        
        print(f"✅ {len(df)}개 종목 스크리닝 완료")
        return df
    
    def _load_stock_list(self) -> pd.DataFrame:
        """종목 리스트 로드 (yfinance 대응용 주요 종목)"""
        try:
            # engine.collectors에서 정의한 주요 종목 리스트 재사용
            from engine.collectors import KR_TOP_STOCKS
            
            stocks = []
            # KR_TOP_STOCKS는 [ (ticker, name, market), ... ] 형식의 리스트임
            for item in KR_TOP_STOCKS:
                ticker_full, name, market = item
                # yfinance 티커(005930.KS)에서 코드(005930)만 추출
                ticker = ticker_full.split('.')[0]
                
                stocks.append({
                    'ticker': ticker,
                    'name': name,
                    'market': market
                })
            
            return pd.DataFrame(stocks)
            
        except Exception as e:
            print(f"Error loading stock list: {e}")
            return pd.DataFrame()

    def _analyze_stock(self, ticker: str, name: str, market: str) -> Optional[VCPResult]:
        """개별 종목 분석 (yfinance + pykrx 기반)"""
        try:
            import yfinance as yf
            
            # 티커 변환
            symbol = f"{ticker}.KS" if market == 'KOSPI' else f"{ticker}.KQ"
            stock_yf = yf.Ticker(symbol)
            
            # 60일 데이터 조회
            df = stock_yf.history(period='3mo')
            if df.empty or len(df) < 20:
                # KOSPI/KOSDAQ 반대로 재시도
                symbol = f"{ticker}.KQ" if market == 'KOSPI' else f"{ticker}.KS"
                df = yf.Ticker(symbol).history(period='3mo')
                if df.empty or len(df) < 20:
                    return None
            
            # VCP 점수 계산 (VCP 패턴 + 수급 점수 합계 100점 만점)
            vcp_score, contraction = self._calculate_vcp_score(df)
            
            # 네이버 금융에서 외인/기관 수급 데이터 크롤링
            foreign_5d = 0
            inst_5d = 0
            try:
                foreign_5d, inst_5d = self._fetch_naver_investor_data(ticker)
            except Exception as e:
                print(f"[Naver] {ticker} 수급 데이터 조회 실패: {e}")
            
            # 수급 점수 계산
            supply_score = 50  # 기본 중립
            if foreign_5d > 0:
                supply_score += min(25, foreign_5d / 100_000_000)  # 1억당 1점, 최대 25점
            elif foreign_5d < 0:
                supply_score -= min(15, abs(foreign_5d) / 100_000_000)
            
            if inst_5d > 0:
                supply_score += min(20, inst_5d / 100_000_000)
            elif inst_5d < 0:
                supply_score -= min(10, abs(inst_5d) / 100_000_000)
            
            supply_score = max(0, min(100, supply_score))
            
            # 외인/기관 트렌드 결정
            foreign_trend = "bullish" if foreign_5d > 0 else ("bearish" if foreign_5d < 0 else "neutral")
            inst_trend = "bullish" if inst_5d > 0 else ("bearish" if inst_5d < 0 else "neutral")
            is_double_buy = foreign_5d > 0 and inst_5d > 0
            
            # 종합 점수 (100점 만점)
            # 수급(70%) + 기술적/VCP(30%)로 재배분하여 1.0을 맞춤
            total_score = (
                supply_score * (self.weight_foreign + self.weight_inst) +
                vcp_score * (self.weight_vcp + self.weight_technical)
            )
            
            # 현재가 정보
            current_price = float(df['Close'].iloc[-1])
            prev_close = float(df['Close'].iloc[-2]) if len(df) > 1 else current_price
            change_pct = ((current_price - prev_close) / prev_close) * 100 if prev_close > 0 else 0
            
            return VCPResult(
                ticker=ticker,
                name=name,
                market=market,
                score=total_score,
                contraction_ratio=contraction,
                foreign_5d=foreign_5d,
                inst_5d=inst_5d,
                foreign_trend=foreign_trend,
                inst_trend=inst_trend,
                is_double_buy=is_double_buy,
                supply_demand_score=supply_score,
                supply_demand_stage="양호" if supply_score >= 60 else ("경계" if supply_score < 40 else "중립"),
                current_price=current_price,
                change_pct=change_pct,
                volume=int(df['Volume'].iloc[-1])
            )
            
        except Exception as e:
            print(f"Error analyzing {ticker}: {e}")
            return None

    def _calculate_vcp_score(self, df: pd.DataFrame) -> Tuple[float, float]:
        """VCP 패턴 점수 계산 (yfinance DataFrame 대응)"""
        if len(df) < 20:
            return 0.0, 0.0
        
        # 고가, 저점, 종가 추출 (컬럼명 대문자 대응)
        high = df['High'].values
        low = df['Low'].values
        close = df['Close'].values
        
        # 최근 20일 변동성 vs 전반부 20일 변동성 비교
        recent_range = (high[-20:].max() - low[-20:].min()) / close[-1]
        early_vol = (high[-40:-20].max() - low[-40:-20].min()) / close[-21] if len(df) >= 40 else recent_range * 1.5
        
        contraction = recent_range / early_vol if early_vol > 0 else 1.0
        
        # 스코어링 로직 (수축이 강할수록 고득점)
        if contraction <= 0.4: score = 100
        elif contraction <= 0.6: score = 80
        elif contraction <= 0.8: score = 50
        else: score = 20
        
        return float(score), float(contraction)

    def _fetch_naver_investor_data(self, ticker: str) -> Tuple[int, int]:
        """네이버 금융에서 외인/기관 순매수 데이터 크롤링 (BeautifulSoup 사용)"""
        import requests
        from bs4 import BeautifulSoup
        
        foreign_5d = 0
        inst_5d = 0
        
        try:
            # 네이버 금융 외국인/기관 페이지
            url = f"https://finance.naver.com/item/frgn.naver?code={ticker}"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            
            res = requests.get(url, headers=headers, timeout=5)
            if res.status_code != 200:
                print(f"[Naver] HTTP {res.status_code} error for {ticker}")
                return 0, 0
            
            soup = BeautifulSoup(res.text, 'html.parser')
            # 날짜별 매매동향 테이블
            rows = soup.select('table.type2 tr')
            
            count = 0
            for row in rows:
                if count >= 5: # 최근 5거래일만 합산
                    break
                    
                cols = row.select('td')
                # 데이터 행은 보통 9개의 td를 가짐 (날짜, 종가, 전일비, 등락률, 거래량, 기관적용, 외인적용, 보유주수, 보유율)
                # 실제 데이터 행인지 확인 (날짜가 들어있는지)
                if len(cols) >= 7:
                    date_td = cols[0].get_text(strip=True)
                    if not date_td or not date_td.replace('.', '').isdigit():
                        continue
                    
                    try:
                        # 기관 순매매량 (보통 index 5)
                        inst_val = int(cols[5].get_text(strip=True).replace(',', '').replace('+', ''))
                        # 외국인 순매매량 (보통 index 6)
                        foreign_val = int(cols[6].get_text(strip=True).replace(',', '').replace('+', ''))
                        
                        inst_5d += inst_val
                        foreign_5d += foreign_val
                        count += 1
                    except (ValueError, IndexError) as e:
                        continue
            
        except Exception as e:
            print(f"[Naver Crawl] {ticker} 오류: {e}")
        
        return foreign_5d, inst_5d
    

    def _calculate_supply_score(self, supply: pd.DataFrame) -> Tuple[int, int, float]:
        """수급 점수 계산"""
        if supply.empty:
            return 0, 0, 50.0
        
        # 최근 5일 순매수
        recent = supply.tail(5)
        
        foreign_5d = 0
        inst_5d = 0
        
        if '외국인순매수' in recent.columns:
            foreign_5d = int(recent['외국인순매수'].sum())
        elif '외국인_순매수' in recent.columns:
            foreign_5d = int(recent['외국인_순매수'].sum())
        
        if '기관순매수' in recent.columns:
            inst_5d = int(recent['기관순매수'].sum())
        elif '기관_순매수' in recent.columns:
            inst_5d = int(recent['기관_순매수'].sum())
        
        # 점수 계산
        score = 50  # 기본 중립
        
        # 외국인 점수 (max 40점)
        if foreign_5d > 5_000_000:
            score += 40
        elif foreign_5d > 2_000_000:
            score += 25
        elif foreign_5d > 1_000_000:
            score += 15
        elif foreign_5d > 0:
            score += 5
        elif foreign_5d < -2_000_000:
            score -= 15
        
        # 기관 점수 (max 30점)
        if inst_5d > 3_000_000:
            score += 30
        elif inst_5d > 1_000_000:
            score += 20
        elif inst_5d > 500_000:
            score += 10
        elif inst_5d > 0:
            score += 5
        elif inst_5d < -1_000_000:
            score -= 10
        
        # 0-100 범위로 제한
        score = max(0, min(100, score))
        
        return foreign_5d, inst_5d, score
    
    def generate_signals(self, df: pd.DataFrame) -> List[Dict]:
        """스크리닝 결과에서 시그널 생성"""
        signals = []
        
        for _, row in df.iterrows():
            if row['score'] >= 70:
                grade = 'A'
            elif row['score'] >= 60:
                grade = 'B'
            else:
                grade = 'C'
            
            signals.append({
                'ticker': str(row['ticker']),
                'name': str(row['name']),
                'market': str(row['market']),
                'score': float(row['score']),
                'grade': grade,
                'contraction_ratio': float(row['contraction_ratio']),
                'foreign_5d': int(row['foreign_5d']),
                'inst_5d': int(row['inst_5d']),
                'is_double_buy': bool(row['is_double_buy']),
                'current_price': float(row['current_price']),
                'signal_date': datetime.now().strftime('%Y-%m-%d'),
                'status': 'OPEN'
            })
        
        return signals


# 테스트용
if __name__ == "__main__":
    screener = SmartMoneyScreener()
    results = screener.run_screening(max_stocks=30)
    
    if not results.empty:
        print("\n📊 스크리닝 결과 (상위 10개):")
        print(results[['ticker', 'name', 'score', 'contraction_ratio', 'foreign_5d', 'inst_5d']].head(10).to_string())
        
        signals = screener.generate_signals(results)
        print(f"\n✅ {len(signals)}개 시그널 생성됨")
