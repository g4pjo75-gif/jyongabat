# app/routes/us_market.py
"""US 마켓 API 라우트"""

import os
import json
import traceback
from datetime import datetime, date
import glob
import yfinance as yf
from flask import Blueprint, jsonify, request

us_bp = Blueprint('us', __name__)

def get_us_data_dir():
    """US 시장 데이터 디렉토리 반환"""
    cwd = os.getcwd()
    data_dir = os.path.join(cwd, 'data', 'us')
    if not os.path.exists(data_dir):
        try:
            os.makedirs(data_dir, exist_ok=True)
        except:
            pass
    return data_dir

@us_bp.route('/market-gate')
def us_market_gate():
    """US Market Gate 상태 (NASDAQ, S&P 500 기반)"""
    try:
        data_dir = get_us_data_dir()
        latest_file = os.path.join(data_dir, 'market_gate_latest.json')
        refresh = request.args.get('refresh', 'false').lower() == 'true'
        
        # 캐시된 데이터가 있고 refresh가 아니면 캐시 반환
        if not refresh and os.path.exists(latest_file):
            with open(latest_file, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
            return jsonify(cached_data)
        
        # 실시간 데이터 조회 (yfinance)
        # ^IXIC: NASDAQ Composite, ^GSPC: S&P 500, ^DJI: Dow Jones
        nasdaq = yf.Ticker("^IXIC")
        sp500 = yf.Ticker("^GSPC")
        dow = yf.Ticker("^DJI")
        
        nasdaq_hist = nasdaq.history(period="5d")
        sp500_hist = sp500.history(period="5d")
        dow_hist = dow.history(period="5d")
        
        def calc_change(hist):
            if hist.empty or len(hist) < 2:
                return 0.0, 0.0
            close = float(hist['Close'].iloc[-1])
            prev = float(hist['Close'].iloc[-2])
            change_pct = ((close - prev) / prev * 100) if prev > 0 else 0
            return round(close, 2), round(change_pct, 2)

        nasdaq_close, nasdaq_change = calc_change(nasdaq_hist)
        sp500_close, sp500_change = calc_change(sp500_hist)
        dow_close, dow_change = calc_change(dow_hist)
        
        # 점수 계산
        avg_change = (nasdaq_change + sp500_change) / 2
        if avg_change >= 1.0:
            status = 'GREEN'
            score = min(100, int(60 + avg_change * 10))
            label = 'BULLISH'
        elif avg_change <= -1.0:
            status = 'RED'
            score = max(0, int(40 + avg_change * 10))
            label = 'BEARISH'
        else:
            status = 'YELLOW'
            score = int(50 + avg_change * 5)
            label = 'NEUTRAL'
        
        # 섹터 데이터 (US 주요 섹터 ETF)
        sectors_data = []
        sector_etfs = [
            ("XLK", "IT/기술주"),
            ("XLV", "헬스케어"),
            ("XLF", "금융"),
            ("XLY", "임의소비재"),
            ("XLP", "필수소비재"),
            ("XLE", "에너지"),
            ("XLI", "산업재"),
            ("XLB", "소재"),
            ("XLRE", "부동산"),
            ("XLC", "통신서비스"),
            ("XLU", "유틸리티")
        ]
        
        # Batch Fetch logic (simplified for US)
        tickers_list = [t for t, n in sector_etfs]
        data = yf.download(tickers_list, period="5d", interval="1d", group_by='ticker', progress=False)
        
        for ticker, name in sector_etfs:
            try:
                if ticker in data.columns.levels[0]:
                    hist = data[ticker]
                    close, change = calc_change(hist)
                    sectors_data.append({
                        'name': name,
                        'signal': 'bullish' if change > 0 else 'bearish',
                        'change_pct': change,
                        'score': int(50 + change * 5)
                    })
            except:
                continue

        reasons = [
            f"NASDAQ {nasdaq_change:+.2f}%",
            f"S&P 500 {sp500_change:+.2f}%",
            f"DOW {dow_change:+.2f}%"
        ]
        
        result_data = {
            'status': status,
            'score': score,
            'label': label,
            'reasons': reasons,
            'sectors': sectors_data,
            'nasdaq_close': nasdaq_close,
            'nasdaq_change_pct': nasdaq_change,
            'sp500_close': sp500_close,
            'sp500_change_pct': sp500_change,
            'dow_close': dow_close,
            'dow_change_pct': dow_change,
            'updated_at': datetime.now().isoformat()
        }
        
        # 캐싱
        if data_dir:
            try:
                with open(latest_file, 'w', encoding='utf-8') as f:
                    json.dump(result_data, f, ensure_ascii=False, indent=2)
            except:
                pass
            
        return jsonify(result_data)
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            'status': 'NEUTRAL',
            'score': 50,
            'label': 'NEUTRAL',
            'sectors': [],
            'error': str(e)
        })

@us_bp.route('/market-gate/dates')
def get_market_gate_dates():
    data_dir = get_us_data_dir()
    if not os.path.exists(data_dir):
        return jsonify([])
    files = glob.glob(os.path.join(data_dir, 'market_gate_*.json'))
    dates = []
    for f in files:
        basename = os.path.basename(f)
        if basename.startswith('market_gate_') and basename != 'market_gate_latest.json':
            date_part = basename[12:20]
            if date_part.isdigit():
                formatted = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:]}"
                dates.append(formatted)
    dates.sort(reverse=True)
    return jsonify(dates)

@us_bp.route('/backtest-summary')
def get_backtest_summary():
    # Placeholder for US Backtest
    return jsonify({
        'closing_bet': {'status': 'Preparing', 'win_rate': 0, 'avg_return': 0, 'count': 0}
    })
