# app/routes/kr_market.py
"""KR 마켓 API 라우트"""

import os
import json
import traceback
from datetime import datetime, date
import glob
import pandas as pd
import yfinance as yf
from flask import Blueprint, jsonify, request, current_app


kr_bp = Blueprint('kr', __name__)

# --- Screener Status Management ---
import threading
import time

class ScreenerManager:
    def __init__(self):
        self.is_running = False
        self.current_task = None  # 'vcp' or 'jongga'
        self.start_time = None
        self.message = ""
        self.lock = threading.Lock()

    def start(self, task_name):
        with self.lock:
            if self.is_running:
                return False
            self.is_running = True
            self.current_task = task_name
            self.start_time = datetime.now()
            self.message = f"Starting {task_name}..."
            return True

    def update_message(self, msg):
        with self.lock:
            self.message = msg

    def stop(self, msg="Completed"):
        with self.lock:
            self.is_running = False
            self.current_task = None
            self.message = msg

screener_manager = ScreenerManager()

@kr_bp.route('/screener/status')
def get_screener_status():
    """스크리너 실행 상태 조회"""
    return jsonify({
        "isRunning": screener_manager.is_running,
        "task": screener_manager.current_task,
        "message": screener_manager.message,
        "startTime": screener_manager.start_time.isoformat() if screener_manager.start_time else None
    })


@kr_bp.route('/market-status')
def get_kr_market_status():
    """한국 시장 상태"""
    try:
        # pykrx로 KOSPI 데이터 조회
        from pykrx import stock
        
        today = date.today().strftime("%Y%m%d")
        
        # KOSPI 지수
        kospi = stock.get_index_ohlcv(today, today, "1001")  # KOSPI
        kosdaq = stock.get_index_ohlcv(today, today, "2001")  # KOSDAQ
        
        kospi_close = float(kospi['종가'].iloc[-1]) if not kospi.empty else 0
        kosdaq_close = float(kosdaq['종가'].iloc[-1]) if not kosdaq.empty else 0
        
        return jsonify({
            'status': 'NEUTRAL',
            'score': 50,
            'kospi': kospi_close,
            'kosdaq': kosdaq_close,
            'date': today,
        })
    except Exception as e:
        print(f"Error checking market status: {e}")
        return jsonify({'error': str(e)}), 500


@kr_bp.route('/signals')
def get_kr_signals():
    """오늘의 시그널 (VCP 우선, 없으면 종가베팅)"""
    try:
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
        vcp_path = os.path.join(data_dir, 'vcp_latest.json')
        jongga_path = os.path.join(data_dir, 'jongga_v2_latest.json')
        
        # VCP 데이터가 있으면 우선 반환
        if os.path.exists(vcp_path):
            with open(vcp_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return jsonify(data)
        
        # 종가베팅 데이터 폴백
        if os.path.exists(jongga_path):
            with open(jongga_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return jsonify(data)
        
        return jsonify({
            'signals': [],
            'count': 0,
            'message': '시그널 데이터가 없습니다.'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@kr_bp.route('/market-gate')
def kr_market_gate():
    """KR Market Gate 상태 (캐시 기반, refresh=true 시 실시간 조회)"""
    try:
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        
        latest_file = os.path.join(data_dir, 'market_gate_latest.json')
        refresh = request.args.get('refresh', 'false').lower() == 'true'
        
        # 캐시된 데이터가 있고 refresh가 아니면 캐시 반환
        if not refresh and os.path.exists(latest_file):
            with open(latest_file, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
            return jsonify(cached_data)
        
        # 실시간 데이터 조회
        from market_gate import run_kr_market_gate
        res = run_kr_market_gate()
        
        # 섹터 데이터 변환
        sectors_data = []
        for s in res.get('sectors', []):
            sectors_data.append({
                'name': s.get('name', ''),
                'signal': s.get('signal', 'neutral'),
                'change_pct': round(s.get('change_1d', 0), 2),
                'score': s.get('score', 50)
            })
        
        result_data = {
            'status': res.get('gate', 'NEUTRAL'),
            'score': res.get('score', 50),
            'label': res.get('label', 'NEUTRAL'),
            'reasons': res.get('reasons', []),
            'sectors': sectors_data,
            'metrics': res.get('metrics', {}),
            'kospi_close': res.get('kospi_close', 0),
            'kospi_change_pct': res.get('kospi_change_pct', 0),
            'kosdaq_close': res.get('kosdaq_close', 0),
            'kosdaq_change_pct': res.get('kosdaq_change_pct', 0),
            'updated_at': datetime.now().isoformat()
        }
        
        # 캐시에 저장 (최신 데이터)
        with open(latest_file, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)
        
        # 일자별 백업 저장
        today_str = date.today().strftime('%Y%m%d')
        daily_file = os.path.join(data_dir, f'market_gate_{today_str}.json')
        with open(daily_file, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)
        
        return jsonify(result_data)
    except Exception as e:
        traceback.print_exc()
        # 캐시가 있으면 캐시 반환
        latest_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'market_gate_latest.json')
        if os.path.exists(latest_file):
            try:
                with open(latest_file, 'r', encoding='utf-8') as f:
                    return jsonify(json.load(f))
            except:
                pass
        # 폴백 응답
        return jsonify({
            'status': 'NEUTRAL',
            'score': 50,
            'label': 'NEUTRAL',
            'sectors': [],
            'error': str(e)
        })


@kr_bp.route('/market-gate/dates', methods=['GET'])
def get_market_gate_dates():
    """Market Gate 데이터가 존재하는 날짜 목록 조회"""
    try:
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
        files = glob.glob(os.path.join(data_dir, 'market_gate_*.json'))
        
        dates = []
        for f in files:
            basename = os.path.basename(f)
            # market_gate_20260125.json 형식에서 날짜 추출
            if basename.startswith('market_gate_') and basename != 'market_gate_latest.json':
                date_part = basename[12:20]  # 20260125
                if len(date_part) == 8 and date_part.isdigit():
                    formatted = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:]}"
                    dates.append(formatted)
        
        dates.sort(reverse=True)
        return jsonify(dates)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@kr_bp.route('/market-gate/history/<date_str>', methods=['GET'])
def get_market_gate_history(date_str):
    """특정 날짜의 Market Gate 데이터 조회"""
    try:
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
        
        # date_str이 2024-01-15 형식이면 20240115로 변환
        if '-' in date_str:
            date_str = date_str.replace('-', '')
        
        filename = f"market_gate_{date_str}.json"
        file_path = os.path.join(data_dir, filename)
        
        if not os.path.exists(file_path):
            return jsonify({"error": "Data not found for this date"}), 404
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@kr_bp.route('/jongga-v2/latest', methods=['GET'])
def get_jongga_v2_latest():
    """종가베팅 v2 최신 결과 조회"""
    try:
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
        latest_file = os.path.join(data_dir, 'jongga_v2_latest.json')
        
        if not os.path.exists(latest_file):
            files = glob.glob(os.path.join(data_dir, 'jongga_v2_results_*.json'))
            if not files:
                return jsonify({
                    "date": date.today().isoformat(),
                    "signals": [],
                    "message": "No data available"
                })
            latest_file = max(files, key=os.path.getctime)
        
        with open(latest_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@kr_bp.route('/jongga-v2/dates', methods=['GET'])
def get_jongga_v2_dates():
    """데이터가 존재하는 날짜 목록 조회"""
    try:
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
        files = glob.glob(os.path.join(data_dir, 'jongga_v2_results_*.json'))
        
        dates = []
        for f in files:
            basename = os.path.basename(f)
            if len(basename) >= 26:
                date_part = basename[18:26]  # 20240115
                formatted = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:]}"
                dates.append(formatted)
        
        dates.sort(reverse=True)
        return jsonify(dates)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@kr_bp.route('/jongga-v2/history/<date_str>', methods=['GET'])
def get_jongga_v2_history(date_str):
    """특정 날짜의 종가베팅 v2 결과 조회"""
    try:
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
        
        # date_str이 2024-01-15 형식이면 20240115로 변환
        if '-' in date_str:
            date_str = date_str.replace('-', '')
        
        filename = f"jongga_v2_results_{date_str}.json"
        file_path = os.path.join(data_dir, filename)
        
        if not os.path.exists(file_path):
            return jsonify({"error": "Data not found for this date"}), 404
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@kr_bp.route('/jongga-v2/run', methods=['POST'])
def run_jongga_v2():
    """전체 종가베팅 v2 엔진 실행 (Background)"""
    if not screener_manager.start('ClosingBet'):
        return jsonify({"status": "error", "message": "Already running"}), 409

    def _run_task():
        try:
            import asyncio
            from engine.generator import run_screener
            
            # 실행 전 데이터 경로 확인
            data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
            if not os.path.exists(data_dir):
                os.makedirs(data_dir)
                
            screener_manager.update_message("Running screener engine (300 stocks)...")
            result = asyncio.run(run_screener(capital=50_000_000))
            
            screener_manager.stop(f"Completed. Filtered: {result.filtered_count}")
        except Exception as e:
            print(f"Error running Jongga V2 engine: {e}")
            traceback.print_exc()
            screener_manager.stop(f"Error: {str(e)}")

    thread = threading.Thread(target=_run_task)
    thread.start()
    
    return jsonify({
        "status": "accepted",
        "message": "Background task started"
    }), 202


@kr_bp.route('/vcp/run', methods=['POST'])
def run_vcp_screener():
    """VCP 패턴 + 수급 스크리너 실행 (Background)"""
    if not screener_manager.start('VCP'):
        return jsonify({"status": "error", "message": "Already running"}), 409

    def _run_task():
        try:
            from screener import SmartMoneyScreener
            
            screener_manager.update_message("Scanning 300 stocks for VCP & Smart Money...")
            screener = SmartMoneyScreener()
            df = screener.run_screening(max_stocks=300) # 300개 전체 스캔
            
            if df.empty:
                screener_manager.stop("No signals found.")
                return
                
            signals = screener.generate_signals(df)
            
            # AI 분석 (제거됨 - 주석 처리하거나 로직 삭제)
            # 여기서는 VCP 결과 저장 로직만 수행
            
            # VCP는 AI 분석 없으므로 바로 저장
            result_data = {
                "updated_at": datetime.now().isoformat(),
                "total_count": len(signals),
                "signals": signals
            }
            
            # 결과 저장
            data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
            if not os.path.exists(data_dir):
                os.makedirs(data_dir)
                
            with open(os.path.join(data_dir, 'vcp_latest.json'), 'w', encoding='utf-8') as f:
                json.dump(result_data, f, ensure_ascii=False, indent=2)
            
            # 일자별 백업 저장
            today_str = date.today().strftime('%Y%m%d')
            daily_file = os.path.join(data_dir, f'vcp_{today_str}.json')
            with open(daily_file, 'w', encoding='utf-8') as f:
                json.dump(result_data, f, ensure_ascii=False, indent=2)

            screener_manager.stop(f"VCP Scan Completed. Found {len(signals)} signals.")
            
        except Exception as e:
            traceback.print_exc()
            screener_manager.stop(f"Error: {str(e)}")

    thread = threading.Thread(target=_run_task)
    thread.start()

    return jsonify({
        "status": "accepted",
        "message": "VCP check started in background"
    }), 202


@kr_bp.route('/vcp/latest', methods=['GET'])
def get_vcp_latest():
    """VCP 최신 결과 조회"""
    try:
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
        vcp_path = os.path.join(data_dir, 'vcp_latest.json')
        
        if os.path.exists(vcp_path):
            with open(vcp_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return jsonify(data)
            
        return jsonify({"signals": [], "message": "No VCP data available"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@kr_bp.route('/vcp/dates', methods=['GET'])
def get_vcp_dates():
    """VCP 데이터가 존재하는 날짜 목록 조회"""
    try:
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
        files = glob.glob(os.path.join(data_dir, 'vcp_*.json'))
        
        dates = []
        for f in files:
            basename = os.path.basename(f)
            # vcp_20260125.json 형식에서 날짜 추출
            if basename.startswith('vcp_') and basename != 'vcp_latest.json':
                date_part = basename[4:12]  # 20260125
                if len(date_part) == 8 and date_part.isdigit():
                    formatted = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:]}"
                    dates.append(formatted)
        
        dates.sort(reverse=True)
        return jsonify(dates)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@kr_bp.route('/vcp/history/<date_str>', methods=['GET'])
def get_vcp_history(date_str):
    """특정 날짜의 VCP 데이터 조회"""
    try:
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
        
        # date_str이 2024-01-15 형식이면 20240115로 변환
        if '-' in date_str:
            date_str = date_str.replace('-', '')
        
        filename = f"vcp_{date_str}.json"
        file_path = os.path.join(data_dir, filename)
        
        if not os.path.exists(file_path):
            return jsonify({"error": "Data not found for this date"}), 404
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def _inject_realtime_prices(data):
    """
    VCP 데이터에 실시간 가격 및 수익률 주입
    - current_price -> entry_price 이동
    - yfinance로 최신가 조회하여 current_price 업데이트
    - return_pct 계산
    """
    try:
        import yfinance as yf
        
        signals = data.get('signals', [])
        if not signals:
            return data
            
        # 티커 맵핑 (ticker -> symbol)
        symbols_map = {}
        for s in signals:
            ticker = s.get('ticker')
            market = s.get('market', '')
            
            if not ticker:
                continue
                
            # 심볼 생성
            if market == 'KOSPI':
                symbol = f"{ticker}.KS"
            elif market == 'KOSDAQ':
                symbol = f"{ticker}.KQ"
            else:
                # 마켓 정보 없으면 시도
                symbol = f"{ticker}.KS" 
                
            symbols_map[symbol] = ticker
            
        if not symbols_map:
            return data
            
        # 가격 일괄 조회
        tickers_list = list(symbols_map.keys())
        # yfinance는 리스트 전달 시 일괄 조회 지원
        # 너무 많으면 나눠서 조회하는게 좋지만, 300개 정도는 괜찮음
        
        print(f"Fetching realtime prices for {len(tickers_list)} stocks...")
        
        # 다운로드 (threads=True로 병렬 다운로드)
        df = yf.download(tickers_list, period="1d", group_by='ticker', threads=True, progress=False)
        
        # 최신가 추출
        latest_prices = {}
        
        # 단일 종목인 경우 구조가 다를 수 있음
        if len(tickers_list) == 1:
            symbol = tickers_list[0]
            if not df.empty:
                try:
                    price = float(df['Close'].iloc[-1])
                    latest_prices[symbols_map[symbol]] = price
                except:
                    pass
        else:
            # 다중 종목
            for symbol in tickers_list:
                try:
                    # Multi-index or normal columns depending on yfinance version
                    if symbol in df.columns.levels[0]: # Top level index is ticker
                        price_series = df[symbol]['Close']
                        if not price_series.empty:
                            price = float(price_series.iloc[-1])
                            latest_prices[symbols_map[symbol]] = price
                except:
                    continue
        
        # 데이터 업데이트
        for s in signals:
            ticker = s.get('ticker')
            
            # 1. entry_price 설정 (기존 current_price 백업)
            # 이미 entry_price가 있다면(재호출 등) 유지, 없다면 current_price 사용
            if 'entry_price' not in s:
                s['entry_price'] = s.get('current_price', 0)
            
            # 2. current_price 업데이트
            if ticker in latest_prices:
                current_price = latest_prices[ticker]
                s['current_price'] = current_price
                
                # 3. 수익률 계산
                entry_price = s.get('entry_price', 0)
                if entry_price > 0:
                    ret = ((current_price - entry_price) / entry_price) * 100
                    s['return_pct'] = round(ret, 2)
                else:
                    s['return_pct'] = 0
            else:
                # 가격 조회 실패 시
                s['return_pct'] = 0
                
        return data
        
    except Exception as e:
        print(f"Error injecting realtime prices: {e}")
        traceback.print_exc()
        return data


@kr_bp.route('/ai-analysis')
def get_kr_ai_analysis():
    """KR AI 분석 전체"""
    try:
        json_path = os.path.join('data', 'jongga_v2_latest.json')
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return jsonify(data)
        return jsonify({'signals': [], 'generated_at': None})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@kr_bp.route('/backtest-summary')
def get_backtest_summary():
    """백테스트 요약"""
    try:
        summary = {
            'vcp': {'status': 'No Data', 'win_rate': 0, 'avg_return': 0, 'count': 0},
            'closing_bet': {'status': 'No Data', 'win_rate': 0, 'avg_return': 0, 'count': 0}
        }
        
        data_dir = os.path.join('data')
        history_files = glob.glob(os.path.join(data_dir, 'jongga_v2_results_*.json'))
        
        if len(history_files) >= 2:
            all_signals = []
            today = datetime.now().strftime('%Y%m%d')
            
            for file_path in sorted(history_files):
                if today in file_path:
                    continue
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    for signal in data.get('signals', []):
                        all_signals.append(signal)
                except:
                    continue
            
            if all_signals:
                wins = sum(1 for s in all_signals if s.get('change_pct', 0) > 0)
                total = len(all_signals)
                win_rate = (wins / total) * 100 if total > 0 else 0
                avg_return = sum(s.get('change_pct', 0) for s in all_signals) / total if total > 0 else 0
                
                summary['closing_bet'] = {
                    'status': 'OK',
                    'count': total,
                    'win_rate': round(win_rate, 1),
                    'avg_return': round(avg_return, 2)
                }
        else:
            summary['closing_bet'] = {
                'status': 'Accumulating',
                'message': f'{len(history_files)}일 데이터 (최소 2일 필요)',
                'count': 0, 'win_rate': 0, 'avg_return': 0
            }
        
        return jsonify(summary)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@kr_bp.route('/jongga-v2/reanalyze/<code>', methods=['POST'])
def reanalyze_single_stock(code):
    """단일 종목 재분석"""
    try:
        import asyncio
        from engine.generator import analyze_single_stock_by_code
        
        result = asyncio.run(analyze_single_stock_by_code(code))
        
        if result:
            return jsonify({
                "status": "success",
                "stock_code": result.stock_code,
                "stock_name": result.stock_name,
                "grade": result.grade.value,
                "score": result.score.total
            })
        else:
            return jsonify({
                "status": "error",
                "message": "재분석 실패 또는 등급 미달"
            }), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@kr_bp.route('/realtime-prices', methods=['POST'])
def get_realtime_prices():
    """실시간 가격 조회 (yfinance Batch)"""
    try:
        import yfinance as yf
        
        data = request.get_json()
        tickers = data.get('tickers', [])
        
        if not tickers:
            return jsonify({})
            
        print(f"Batch fetching prices for {len(tickers)} stocks...")
        
        # 티커 변환
        valid_tickers = []
        ticker_map = {} # symbol -> original_ticker
        
        for t in tickers:
            # .KS나 .KQ가 없으면 붙여서 시도
            if not t.endswith('.KS') and not t.endswith('.KQ'):
                # 우선 .KS로 가정, 둘 다 시도할 수도 있음
                # 여기서는 간단히 .KS로 변환
                symbol = f"{t}.KS"
                valid_tickers.append(symbol)
                ticker_map[symbol] = t
                
                # 혹시 모르니 .KQ도 추가? (yfinance는 알아서 필터링함)
                symbol_kq = f"{t}.KQ"
                valid_tickers.append(symbol_kq)
                ticker_map[symbol_kq] = t
            else:
                valid_tickers.append(t)
                ticker_map[t] = t
        
        # Batch Download
        # threads=True (기본값)
        print(f"Downloading tickers: {valid_tickers}")
        df = yf.download(valid_tickers, period="1d", group_by='ticker', progress=False)
        
        print(f"Downloaded shape: {df.shape}")
        print(f"Columns: {df.columns}")
        
        prices = {}
        
        if df.empty:
            print("DataFrame is empty!")
            return jsonify({})
            
        # 결과 파싱
        # 단일 종목일 경우와 다중 종목일 경우 구조가 다름
        if len(valid_tickers) == 1:
             try:
                 symbol = valid_tickers[0]
                 # GroupBy ticker results in single level if only 1 ticker? No, usually not with group_by
                 # But let's handle standard case
                 series = None
                 if isinstance(df.columns, pd.MultiIndex):
                      if symbol in df.columns.levels[0]:
                          series = df[symbol]['Close']
                      else:
                          # Try finding symbol in level 1
                          try:
                              series = df.xs(symbol, level=1, axis=1)['Close']
                          except:
                              pass
                 else:
                      series = df['Close']
                      
                 if series is not None:
                     valid_series = series.dropna()
                     if not valid_series.empty:
                         price = float(valid_series.iloc[-1])
                         original_ticker = ticker_map.get(symbol, symbol)
                         prices[original_ticker] = price
             except Exception as e:
                 print(f"Error parsing single ticker: {e}")
                 pass
        else:
            # Flatten columns for easier search if needed or inspect structure
            # cols_flat = ["_".join(map(str, c)) if isinstance(c, tuple) else str(c) for c in df.columns]
            # print(f"Flat columns sample: {cols_flat[:10]}")
            
            for symbol in valid_tickers:
                try:
                    series = None
                    
                    # 1. Standard group_by='ticker' (Ticker, Price)
                    if isinstance(df.columns, pd.MultiIndex) and symbol in df.columns.levels[0]:
                        series = df[symbol]['Close']
                    
                    # 2. Maybe (Price, Ticker) if group_by failed?
                    elif isinstance(df.columns, pd.MultiIndex) and symbol in df.columns.levels[1]:
                         try:
                             series = df.xs(symbol, level=1, axis=1)['Close']
                         except:
                             try:
                                 series = df['Close'][symbol]
                             except:
                                 pass
                                 
                    # 3. Direct access (flat columns)
                    elif symbol in df.columns:
                        series = df[symbol]['Close']
                    
                    if series is not None:
                        valid_series = series.dropna()
                        if not valid_series.empty:
                            price = float(valid_series.iloc[-1])
                            # 원본 티커로 매핑 (KS/KQ 제거된 형태 등)
                            original_ticker = ticker_map.get(symbol)
                            if original_ticker:
                                prices[original_ticker] = price
                except:
                    continue
                    
        print(f"Fetched {len(prices)} prices.")
        return jsonify(prices)
        
    except Exception as e:
        print(f"Error fetching realtime prices: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# Chatbot API endpoints
_chatbot_instances = {}

@kr_bp.route('/chatbot/message', methods=['POST'])
def chatbot_message():
    """챗봇 메시지 처리"""
    try:
        from chatbot import KRStockChatbot
        
        data = request.get_json()
        user_id = data.get('user_id', 'default')
        message = data.get('message', '')
        
        if not message:
            return jsonify({'error': 'No message provided'}), 400
        
        # 사용자별 챗봇 인스턴스 관리
        if user_id not in _chatbot_instances:
            _chatbot_instances[user_id] = KRStockChatbot(user_id)
        
        chatbot = _chatbot_instances[user_id]
        response = chatbot.chat(message)
        
        return jsonify({
            'response': response,
            'user_id': user_id
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@kr_bp.route('/chatbot/welcome', methods=['GET'])
def chatbot_welcome():
    """챗봇 웰컴 메시지"""
    try:
        from chatbot import KRStockChatbot
        
        user_id = request.args.get('user_id', 'default')
        
        if user_id not in _chatbot_instances:
            _chatbot_instances[user_id] = KRStockChatbot(user_id)
        
        chatbot = _chatbot_instances[user_id]
        welcome = chatbot.get_welcome()
        
        return jsonify({
            'message': welcome,
            'user_id': user_id
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500





@kr_bp.route('/performance/analyze', methods=['POST'])
def analyze_performance():
    """성과 분석 (과거 포착 종목의 이후 주가 추적)"""
    try:
        import yfinance as yf
        from datetime import datetime, timedelta
        import os
        import json
        import pandas as pd
        
        req_data = request.get_json()
        target_date_str = req_data.get('date') # 2026-01-20
        
        if not target_date_str:
            return jsonify({'error': 'Date is required'}), 400
            
        # load signal data
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
        date_nohol = target_date_str.replace('-', '')
        filename = f"jongga_v2_results_{date_nohol}.json"
        vcp_filename = f"vcp_{date_nohol}.json"
        
        # Try finding jongga first, then vcp
        file_path = os.path.join(data_dir, filename)
        if not os.path.exists(file_path):
             file_path = os.path.join(data_dir, vcp_filename)
             if not os.path.exists(file_path):
                 return jsonify({'error': f'Data not found for {target_date_str}'}), 404
             
        with open(file_path, 'r', encoding='utf-8') as f:
            signal_data = json.load(f)
            
        signals = signal_data.get('signals', [])
        if not signals:
             return jsonify({'dates': [], 'rows': []})
        
        # Collect tickers
        tickers = []
        ticker_map = {} # symbol -> signal object
        for s in signals:
            code = s.get('stock_code') or s.get('ticker')
            if not code: continue
            
            market = s.get('market', '')
            suffix = '.KQ' if market == 'KOSDAQ' or market == 'KQ' else '.KS'
            symbol = f"{code}{suffix}"
            tickers.append(symbol)
            ticker_map[symbol] = s
            ticker_map[code] = s 
            
        if not tickers:
             return jsonify({'dates': [], 'rows': []})
             
        # Fetch History
        print(f"Analyzing performance for {target_date_str} to now. Tickers: {len(tickers)}")
        
        # Download
        df = yf.download(tickers, start=target_date_str, group_by='ticker', progress=False, threads=False)
        
        if df.empty:
             return jsonify({'dates': [], 'rows': []})
             
        # Extract and Filter dates
        all_dates = [d.strftime('%Y-%m-%d') for d in df.index]
        
        market_dates = []
        if all_dates:
            start_d = datetime.strptime(all_dates[0], '%Y-%m-%d')
            limit_d = start_d + timedelta(days=7) # Capture date + 7 days
            
            # 1. Add dates within 1 week
            for d in all_dates:
                curr = datetime.strptime(d, '%Y-%m-%d')
                if curr <= limit_d:
                    market_dates.append(d)
            
            # 2. Add latest date (Today) if not included
            if all_dates[-1] not in market_dates:
                market_dates.append(all_dates[-1])
        
        # Build Rows
        rows = []
        is_multi = len(tickers) > 1
        
        for symbol in tickers:
            s = ticker_map.get(symbol)
            if not s: continue
            
            row = {
                'signal_info': s,
                'daily_stats': []
            }
            
            try:
                # Get close series
                series = None
                if is_multi:
                     if isinstance(df.columns, pd.MultiIndex):
                         if symbol in df.columns.levels[0]:
                             series = df[symbol]['Close']
                         elif symbol.replace('.KS', '.KQ') in df.columns.levels[0]:
                              series = df[symbol.replace('.KS', '.KQ')]['Close']
                else:
                    if isinstance(df.columns, pd.MultiIndex):
                         if symbol in df.columns.levels[0]:
                             series = df[symbol]['Close']
                         else:
                             series = df['Close']
                    else:
                        series = df['Close']
                        
                if series is not None:
                    entry_price = s.get('current_price') or s.get('entry_price')
                    
                    for date_val in df.index:
                        d_str = date_val.strftime('%Y-%m-%d')
                        if d_str not in market_dates: continue
                        
                        try:
                            val = float(series.loc[date_val])
                            if pd.isna(val):
                                row['daily_stats'].append({'date': d_str, 'close': None, 'return_pct': None})
                            else:
                                ret = 0
                                if entry_price and entry_price > 0:
                                    ret = ((val - entry_price) / entry_price) * 100
                                row['daily_stats'].append({
                                    'date': d_str, 
                                    'close': val, 
                                    'return_pct': round(ret, 2)
                                })
                        except:
                             row['daily_stats'].append({'date': d_str, 'close': None, 'return_pct': None})
            except Exception as e:
                pass
                
            rows.append(row)
            
        return jsonify({
            'dates': market_dates,
            'rows': rows
        })
        
    except Exception as e:
        print("Analysis Error:", e)
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
