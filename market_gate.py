"""
Market Gate - 시장 상태 분석
yfinance 기반 지수 데이터 조회
"""

from datetime import date, timedelta
from typing import Dict, List
from dataclasses import dataclass
import yfinance as yf


@dataclass
class SectorInfo:
    """섹터 정보"""
    name: str
    ticker: str
    signal: str = "neutral"
    change_1d: float = 0.0
    score: int = 50


def run_kr_market_gate() -> Dict:
    """KR Market Gate 분석 실행 (yfinance 기반)"""
    try:
        # KOSPI 지수 (^KS11), KOSDAQ (^KQ11)
        kospi_ticker = yf.Ticker("^KS11")
        kosdaq_ticker = yf.Ticker("^KQ11")
        
        # 최근 5일 데이터 조회
        kospi_hist = kospi_ticker.history(period="5d")
        kosdaq_hist = kosdaq_ticker.history(period="5d")
        
        # KOSPI
        if not kospi_hist.empty and len(kospi_hist) >= 2:
            kospi_close = float(kospi_hist['Close'].iloc[-1])
            kospi_prev = float(kospi_hist['Close'].iloc[-2])
            kospi_change_pct = ((kospi_close - kospi_prev) / kospi_prev * 100) if kospi_prev > 0 else 0
        else:
            kospi_close = 0
            kospi_change_pct = 0
        
        # KOSDAQ
        if not kosdaq_hist.empty and len(kosdaq_hist) >= 2:
            kosdaq_close = float(kosdaq_hist['Close'].iloc[-1])
            kosdaq_prev = float(kosdaq_hist['Close'].iloc[-2])
            kosdaq_change_pct = ((kosdaq_close - kosdaq_prev) / kosdaq_prev * 100) if kosdaq_prev > 0 else 0
        else:
            kosdaq_close = 0
            kosdaq_change_pct = 0
        
        # 섹터 ETF 분석 (한국 ETF - yfinance 티커)
        sector_etfs = {
            "반도체": "091160.KS",      # KODEX 반도체
            "2차전지": "305720.KS",     # KODEX 2차전지산업
            "자동차": "091170.KS",      # KODEX 자동차
            "헬스케어": "091180.KS",    # TIGER 200 헬스케어
            "IT": "139260.KS",          # TIGER 200 IT
            "철강/조선": "091190.KS",   # TIGER 200 중공업
        }
        
        sectors = []
        for name, ticker in sector_etfs.items():
            try:
                etf = yf.Ticker(ticker)
                hist = etf.history(period="5d")
                
                if not hist.empty and len(hist) >= 2:
                    close = float(hist['Close'].iloc[-1])
                    prev = float(hist['Close'].iloc[-2])
                    change = ((close - prev) / prev * 100) if prev > 0 else 0
                    
                    signal = "neutral"
                    if change >= 1.0:
                        signal = "bullish"
                    elif change <= -1.0:
                        signal = "bearish"
                    
                    sectors.append(SectorInfo(
                        name=name,
                        ticker=ticker.replace(".KS", ""),
                        signal=signal,
                        change_1d=round(change, 2),
                        score=max(0, min(100, 50 + int(change * 10)))
                    ))
            except Exception as e:
                print(f"[Sector] {name} error: {e}")
                continue
        
        # 전체 점수 계산
        avg_change = (kospi_change_pct + kosdaq_change_pct) / 2
        score = 50 + int(avg_change * 10)
        score = max(0, min(100, score))
        
        # 게이트 결정
        if score >= 70:
            gate = "GREEN"
            label = "BULLISH"
        elif score >= 40:
            gate = "YELLOW"
            label = "NEUTRAL"
        else:
            gate = "RED"
            label = "BEARISH"
        
        # 이유
        reasons = []
        if kospi_change_pct >= 1.0:
            reasons.append("KOSPI 강세")
        elif kospi_change_pct <= -1.0:
            reasons.append("KOSPI 약세")
        
        if kosdaq_change_pct >= 1.0:
            reasons.append("KOSDAQ 강세")
        elif kosdaq_change_pct <= -1.0:
            reasons.append("KOSDAQ 약세")
        
        return {
            'gate': gate,
            'score': score,
            'label': label,
            'reasons': reasons,
            'sectors': [
                {
                    'name': s.name,
                    'signal': s.signal,
                    'change_1d': s.change_1d,
                    'score': s.score
                } for s in sectors
            ],
            'metrics': {
                'kospi_change': round(kospi_change_pct, 2),
                'kosdaq_change': round(kosdaq_change_pct, 2),
            },
            'kospi_close': round(kospi_close, 2),
            'kospi_change_pct': round(kospi_change_pct, 2),
            'kosdaq_close': round(kosdaq_close, 2),
            'kosdaq_change_pct': round(kosdaq_change_pct, 2),
        }
        
    except Exception as e:
        print(f"[Market Gate] Error: {e}")
        import traceback
        traceback.print_exc()
        return {
            'gate': 'YELLOW',
            'score': 50,
            'label': 'NEUTRAL',
            'reasons': [f'Error: {str(e)}'],
            'sectors': [],
            'metrics': {},
            'kospi_close': 0,
            'kospi_change_pct': 0,
            'kosdaq_close': 0,
            'kosdaq_change_pct': 0,
        }


if __name__ == "__main__":
    result = run_kr_market_gate()
    import json
    print(json.dumps(result, ensure_ascii=False, indent=2))
