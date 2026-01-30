"""
일본 주식 VCP 스크리너 - 니케이 225/400 시그널 기반
VCP(Volatility Contraction Pattern) + 수급 분석
"""

import os
import json
import asyncio
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
from engine.models import StockData, ChartData

class JPVCPScreener:
    """니케이 225/400 상위 시그널 대상 VCP 분석가"""
    
    def __init__(self):
        self.data_dir = os.path.join(os.getcwd(), 'data', 'jp')
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir, exist_ok=True)
            
    async def run_vcp_scan(self) -> Dict:
        """VCP 스캔 실행"""
        try:
            # 1. 대상 종목 로드
            targets = self._load_target_stocks()
            if not targets:
                return {"status": "error", "message": "No target signals found."}
            
            print(f"[JP VCP] Scan Targets: {len(targets)} stocks")
            
            # 2. 일괄 데이터 다운로드 (Rate Limit 방지 및 속도 향상)
            tickers = [f"{t['code']}.T" for t in targets]
            df_all = yf.download(tickers, period="3mo", progress=False, group_by='ticker')
            
            results = []
            for stock in targets:
                code = stock['code']
                ticker_key = f"{code}.T"
                
                try:
                    df = df_all[ticker_key].dropna()
                    if df.empty or len(df) < 40:
                        continue
                    
                    # 3. VCP 분석
                    vcp_info = self._analyze_vcp_df(df)
                    
                    # 4. 수급 분석 (추정치 포함)
                    supply_info = self._analyze_supply_df(df)
                    
                    # 5. 최종 점수 및 등급
                    total_score = (vcp_info['vcp_score'] * 0.5) + (supply_info['supply_score'] * 0.5)
                    
                    if total_score >= 80: grade = 'S'
                    elif total_score >= 70: grade = 'A'
                    elif total_score >= 60: grade = 'B'
                    else: grade = 'C'
                    
                    results.append({
                        'code': code,
                        'name': stock['name'],
                        'market': stock.get('market', 'TSE'),
                        'sector': stock.get('sector', '-'),
                        'score': round(total_score, 1),
                        'grade': grade,
                        'vcp_score': vcp_info['vcp_score'],
                        'supply_score': supply_info['supply_score'],
                        'contraction_ratio': vcp_info['contraction_ratio'],
                        'foreign_5d': supply_info['foreign_5d'],
                        'inst_5d': supply_info['inst_5d'],
                        'is_double_buy': supply_info['is_double_buy'],
                        'current_price': vcp_info['current_price'],
                        'change_pct': stock.get('change_pct', 0),
                        'updated_at': datetime.now().isoformat()
                    })
                except Exception as e:
                    print(f"[JP VCP] Error analyzing {code}: {e}")
                    continue
            
            # 점수순 정렬
            results.sort(key=lambda x: x['score'], reverse=True)
            
            final_data = {
                "generated_at": datetime.now().isoformat(),
                "total_count": len(results),
                "signals": results
            }
            
            # 결과 저장
            save_path = os.path.join(self.data_dir, 'vcp_latest.json')
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(final_data, f, ensure_ascii=False, indent=2)
                
            daily_path = os.path.join(self.data_dir, f"vcp_{date.today().strftime('%Y%m%d')}.json")
            with open(daily_path, 'w', encoding='utf-8') as f:
                json.dump(final_data, f, ensure_ascii=False, indent=2)
                
            print(f"[JP VCP] Scan Completed. Found {len(results)} signals.")
            return final_data
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"status": "error", "message": str(e)}

    def _load_target_stocks(self) -> List[Dict]:
        targets = []
        codes_seen = set()
        for type_key in ['n225', 'n400']:
            path = os.path.join(self.data_dir, f'jongga_v2_{type_key}_latest.json')
            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        signals = data.get('signals', [])
                        for s in signals:
                            code = s['code']
                            if code not in codes_seen:
                                targets.append(s)
                                codes_seen.add(code)
                except: continue
        return targets

    def _analyze_vcp_df(self, df: pd.DataFrame) -> Dict:
        high = df['High'].values
        low = df['Low'].values
        close_vals = df['Close'].values
        current_close = float(close_vals[-1])
        
        # 최근 20일 변동성 vs 그 이전 20일 변동성
        recent_range = (np.max(high[-20:]) - np.min(low[-20:])) / current_close
        prev_range = (np.max(high[-40:-20:]) - np.min(low[-40:-20:])) / close_vals[-21]
        
        contraction = recent_range / prev_range if prev_range > 0 else 1.0
        
        if contraction <= 0.4: v_score = 100
        elif contraction <= 0.6: v_score = 80
        elif contraction <= 0.8: v_score = 60
        elif contraction <= 1.0: v_score = 40
        else: v_score = 20
        
        return {
            'vcp_score': float(v_score),
            'contraction_ratio': round(float(contraction), 2),
            'current_price': float(current_close)
        }

    def _analyze_supply_df(self, df: pd.DataFrame) -> Dict:
        """수급 데이터 분석 (기술적 데이터 기반 추정 포함)"""
        supply_score = 60.0 # 기본 시작 점수
        
        close = df['Close'].values
        volume = df['Volume'].values
        
        # 5일 평균 거래량 대비 최근 거래량
        vol_avg_5d = np.mean(volume[-10:-5])
        vol_recent = np.mean(volume[-5:])
        
        vol_ratio = float(vol_recent / vol_avg_5d) if vol_avg_5d > 0 else 1.0
        
        # 5일 이동평균선 상향 돌파 여부
        ma5 = df['Close'].rolling(5).mean().values
        price_trend = bool(close[-1] > ma5[-1])
        
        # 주가 누적 변동 (5일간)
        price_change_5d = (close[-1] - close[-5]) / close[-5] if len(close) >= 5 else 0
        
        # 수급 추정 로직 개선: 거래량 변화가 적더라도 주가가 견조하면 점진적 수급 유입으로 간주
        # vol_ratio가 1.0 근처여도 price_trend가 양호하면 기본 수급이 있는 것으로 추산
        base_flow = (vol_ratio - 0.9) * 2000000 
        
        if price_trend:
            if vol_ratio > 1.2:
                supply_score += 15
                f_mult, i_mult = 1.2, 0.8
            else:
                supply_score += 5
                f_mult, i_mult = 0.8, 0.5
        else:
            if vol_ratio > 1.2:
                # 하락 거래량 실린 경우 (매도세)
                supply_score -= 10
                f_mult, i_mult = -1.5, -1.0
            else:
                supply_score -= 5
                f_mult, i_mult = -0.6, -0.4
        
        foreign_5d = int(base_flow * f_mult)
        inst_5d = int(base_flow * i_mult)
            
        return {
            'supply_score': min(100.0, max(0.0, float(supply_score))),
            'foreign_5d': foreign_5d,
            'inst_5d': inst_5d,
            'is_double_buy': bool(price_trend and vol_ratio > 1.5)
        }

if __name__ == "__main__":
    screener = JPVCPScreener()
    asyncio.run(screener.run_vcp_scan())
