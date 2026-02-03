# app/routes/jp_market.py
"""JP 마켓 API 라우트 (일본 시장)"""

import os
import json
import traceback
import re
from datetime import datetime, date
import glob
import pandas as pd
import yfinance as yf
from flask import Blueprint, jsonify, request, current_app

import threading
import time

jp_bp = Blueprint('jp', __name__)


# --- Screener Status Management ---
class JPScreenerManager:
    def __init__(self):
        self.is_running = False
        self.current_task = None
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


jp_screener_manager = JPScreenerManager()
# Force reset on import (ensures clean state after server restart)
jp_screener_manager.is_running = False
jp_screener_manager.current_task = None
jp_screener_manager.start_time = None
jp_screener_manager.message = ""


def get_jp_data_dir():
    """일본 시장 데이터 디렉토리 반환"""
    # Use cwd as primary, __file__ as backup
    cwd = os.getcwd()
    data_dir = os.path.join(cwd, 'data', 'jp')
    if not os.path.exists(data_dir):
        # Fallback to relative from file logic
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'jp')
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
    return data_dir


# === 스크리너 상태 ===
@jp_bp.route('/screener/status')
def get_screener_status():
    """스크리너 실행 상태 조회"""
    return jsonify({
        "isRunning": jp_screener_manager.is_running,
        "task": jp_screener_manager.current_task,
        "message": jp_screener_manager.message,
        "startTime": jp_screener_manager.start_time.isoformat() if jp_screener_manager.start_time else None
    })


@jp_bp.route('/screener/reset', methods=['POST'])
def reset_screener_status():
    """스크리너 상태 강제 리셋"""
    jp_screener_manager.stop("Reset by user")
    return jsonify({"status": "ok", "message": "Screener status reset"})


# === Market Gate ===
@jp_bp.route('/market-gate')
def jp_market_gate():
    """JP Market Gate 상태 (Nikkei 225 / TOPIX 기반)"""
    try:
        data_dir = get_jp_data_dir()
        latest_file = os.path.join(data_dir, 'market_gate_latest.json')
        refresh = request.args.get('refresh', 'false').lower() == 'true'
        
        # 캐시된 데이터가 있고 refresh가 아니면 캐시 반환
        if not refresh and os.path.exists(latest_file):
            with open(latest_file, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
            return jsonify(cached_data)
        
        # 실시간 데이터 조회 (yfinance)
        # ^N225 for Nikkei, 1306.T ETF for TOPIX (^TPX doesn't work)
        nikkei = yf.Ticker("^N225")
        topix_etf = yf.Ticker("1306.T")  # TOPIX連動型ETF (^TPX는 yfinance에서 작동 안함)
        
        nikkei_hist = nikkei.history(period="5d")
        topix_hist = topix_etf.history(period="5d")
        
        nikkei_close = float(nikkei_hist['Close'].iloc[-1]) if not nikkei_hist.empty else 0
        nikkei_prev = float(nikkei_hist['Close'].iloc[-2]) if len(nikkei_hist) > 1 else nikkei_close
        nikkei_change_pct = ((nikkei_close - nikkei_prev) / nikkei_prev * 100) if nikkei_prev > 0 else 0
        
        # TOPIX ETF 가격 (실제 TOPIX 지수는 ETF 가격 * 약간의 비율이지만, 변동률은 동일)
        topix_etf_close = float(topix_hist['Close'].iloc[-1]) if not topix_hist.empty else 0
        topix_etf_prev = float(topix_hist['Close'].iloc[-2]) if len(topix_hist) > 1 else topix_etf_close
        topix_change_pct = ((topix_etf_close - topix_etf_prev) / topix_etf_prev * 100) if topix_etf_prev > 0 else 0
        # TOPIX ETF 가격을 대략적인 TOPIX 지수로 환산 (ETF 가격 ≈ TOPIX / 10)
        topix_close = topix_etf_close * 0.7  # 대략적인 환산 (1306.T 기준)
        
        # 점수 계산 (간단한 버전)
        avg_change = (nikkei_change_pct + topix_change_pct) / 2
        if avg_change >= 1.5:
            status = 'GREEN'
            score = min(100, int(50 + avg_change * 10))
            label = 'BULLISH'
        elif avg_change <= -1.5:
            status = 'RED'
            score = max(0, int(50 + avg_change * 10))
            label = 'BEARISH'
        else:
            status = 'YELLOW'
            score = int(50 + avg_change * 5)
            label = 'NEUTRAL'
        
        # 섹터 데이터 (일본 주요 섹터 ETF)
        sectors_data = []
        sector_etfs = [
            # 주요 지수 ETF
            ("1321.T", "닛케이225", "index"),      # NEXT FUNDS 日経225連動型ETF
            ("1306.T", "TOPIX", "index"),          # TOPIX連動型ETF
            # 섹터별 ETF
            ("1617.T", "식품", "sector"),           # NOMURA 食品
            ("1618.T", "에너지", "sector"),         # NOMURA エネルギー資源
            ("1619.T", "건설", "sector"),           # NOMURA 建設・資材
            ("1620.T", "소재", "sector"),           # NOMURA 素材・化学
            ("1621.T", "의료", "sector"),           # NOMURA 医薬品
            ("1625.T", "은행", "sector"),           # NOMURA 銀行
            ("1628.T", "운송", "sector"),           # NOMURA 運輸・物流
            ("1633.T", "전자", "sector"),           # NOMURA 電機・精密
        ]
        
        for ticker, name, stype in sector_etfs:
            try:
                etf = yf.Ticker(ticker)
                hist = etf.history(period="5d")
                if not hist.empty and len(hist) >= 2:
                    close = float(hist['Close'].iloc[-1])
                    prev = float(hist['Close'].iloc[-2])
                    change = ((close - prev) / prev * 100) if prev > 0 else 0
                    sectors_data.append({
                        'name': name,
                        'signal': 'bullish' if change > 0 else 'bearish',
                        'change_pct': round(change, 2),
                        'score': int(50 + change * 5)
                    })
            except:
                continue
        
        reasons = []
        if nikkei_change_pct > 0:
            reasons.append(f"日経225 +{nikkei_change_pct:.2f}%")
        else:
            reasons.append(f"日経225 {nikkei_change_pct:.2f}%")
        if topix_change_pct > 0:
            reasons.append(f"TOPIX +{topix_change_pct:.2f}%")
        else:
            reasons.append(f"TOPIX {topix_change_pct:.2f}%")
        
        result_data = {
            'status': status,
            'score': score,
            'label': label,
            'reasons': reasons,
            'sectors': sectors_data,
            'metrics': {},
            'nikkei_close': round(nikkei_close, 2),
            'nikkei_change_pct': round(nikkei_change_pct, 2),
            'topix_close': round(topix_close, 2),
            'topix_change_pct': round(topix_change_pct, 2),
            'updated_at': datetime.now().isoformat()
        }
        
        # 캐시에 저장
        with open(latest_file, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)
        
        # 일자별 백업
        today_str = date.today().strftime('%Y%m%d')
        daily_file = os.path.join(data_dir, f'market_gate_{today_str}.json')
        with open(daily_file, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)
        
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


@jp_bp.route('/market-gate/dates', methods=['GET'])
def get_market_gate_dates():
    """Market Gate 데이터가 존재하는 날짜 목록"""
    try:
        data_dir = get_jp_data_dir()
        files = glob.glob(os.path.join(data_dir, 'market_gate_*.json'))
        
        dates = []
        for f in files:
            basename = os.path.basename(f)
            if basename.startswith('market_gate_') and basename != 'market_gate_latest.json':
                date_part = basename[12:20]
                if len(date_part) == 8 and date_part.isdigit():
                    formatted = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:]}"
                    dates.append(formatted)
        
        dates.sort(reverse=True)
        return jsonify(dates)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@jp_bp.route('/market-gate/history/<date_str>', methods=['GET'])
def get_market_gate_history(date_str):
    """특정 날짜의 Market Gate 데이터"""
    try:
        data_dir = get_jp_data_dir()
        
        if '-' in date_str:
            date_str = date_str.replace('-', '')
        
        filename = f"market_gate_{date_str}.json"
        file_path = os.path.join(data_dir, filename)
        
        if not os.path.exists(file_path):
            return jsonify({"error": "Data not found"}), 404
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# === 시그널 조회 ===
@jp_bp.route('/signals')
def get_jp_signals():
    """오늘의 시그널"""
    try:
        data_dir = get_jp_data_dir()
        jongga_path = os.path.join(data_dir, 'jongga_v2_latest.json')
        
        if os.path.exists(jongga_path):
            with open(jongga_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return jsonify(data)
        
        return jsonify({
            'signals': [],
            'count': 0,
            'message': 'シグナルデータがありません。'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# === 종가베팅 (Closing Bet) ===
@jp_bp.route('/jongga-v2/latest', methods=['GET'])
def get_jongga_v2_latest():
    """종가베팅 v2 최신 결과 (type=n225|n400)"""
    try:
        signal_type = request.args.get('type', 'n225') # default n225
        data_dir = get_jp_data_dir()
        
        # Select file based on type
        prefix = 'jongga_v2_n400_' if signal_type == 'n400' else 'jongga_v2_n225_'
        latest_file = os.path.join(data_dir, f'{prefix}latest.json')
        # if not os.path.exists(latest_file):
            # ... skipped fallback logic for now ...
        
        if not os.path.exists(latest_file):
            print(f"DEBUG: File not found: {latest_file}")
            return jsonify({
                "date": date.today().isoformat(),
                "signals": [],
                "message": "No data available"
            }) 

        print(f"DEBUG: Attempting to open {latest_file}")
        
        with open(latest_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@jp_bp.route('/jongga-v2/dates', methods=['GET'])
def get_jongga_v2_dates():
    """데이터가 존재하는 날짜 목록 (type=n225|n400)"""
    try:
        signal_type = request.args.get('type', 'n225')
        data_dir = get_jp_data_dir()
        prefix = 'jongga_v2_n400_' if signal_type == 'n400' else 'jongga_v2_n225_'
        
        files = glob.glob(os.path.join(data_dir, f'{prefix}results_*.json'))
        
        dates = []
        for f in files:
            basename = os.path.basename(f)
            # Pattern: jongga_v2_n{type}_results_{date}.json
            match = re.search(r'results_(\d{8})\.json', basename)
            if match:
                date_part = match.group(1)
                formatted = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:]}"
                dates.append(formatted)
        
        # Add legacy dates for n225
        if signal_type == 'n225':
            legacy_files = glob.glob(os.path.join(data_dir, 'jongga_v2_results_*.json'))
            for f in legacy_files:
                basename = os.path.basename(f)
                match = re.search(r'results_(\d{8})\.json', basename)
                if match:
                    date_part = match.group(1)
                    formatted = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:]}"
                    dates.append(formatted)
        
        dates = list(set(dates)) # remove duplicates
        dates.sort(reverse=True)
        return jsonify(dates)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@jp_bp.route('/jongga-v2/history/<date_str>', methods=['GET'])
def get_jongga_v2_history(date_str):
    """특정 날짜의 종가베팅 결과"""
    try:
        signal_type = request.args.get('type', 'n225')
        data_dir = get_jp_data_dir()
        
        if '-' in date_str:
            date_str = date_str.replace('-', '')
        
        prefix = 'jongga_v2_n400_' if signal_type == 'n400' else 'jongga_v2_n225_'
        filename = f"{prefix}results_{date_str}.json"
        file_path = os.path.join(data_dir, filename)
        
        # Fallback
        if not os.path.exists(file_path) and signal_type == 'n225':
             legacy_path = os.path.join(data_dir, f"jongga_v2_results_{date_str}.json")
             if os.path.exists(legacy_path):
                 file_path = legacy_path
        
        if not os.path.exists(file_path):
            return jsonify({"error": "Data not found"}), 404
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@jp_bp.route('/jongga-v2/run', methods=['POST'])
def run_jongga_v2():
    """일본 종가베팅 스크리너 실행 (Background) - Supports n225, n400, or all"""
    run_type = request.args.get('type', 'all')  # n225, n400, all
    
    task_name = f"JP_ClosingBet_{run_type.upper()}"
    if not jp_screener_manager.start(task_name):
        return jsonify({"status": "error", "message": "Already running"}), 409

    def _run_task(target_type):
        try:
            import asyncio
            from engine.jp_collectors import JPXCollector, YahooJapanNewsCollector
            from engine.jp_config import JPSignalConfig
            from engine.scorer import Scorer
            # from engine.models import Signal # Unused
            from engine.jp_stock_list import get_n225_list
            
            # Identify N225 Set for checking
            n225_stocks = get_n225_list()
            n225_codes = set([s[0] for s in n225_stocks]) # "6501.T"
            
            data_dir = get_jp_data_dir()
            
            base_msg = "JPX Nikkei 400"
            if target_type == 'n225': base_msg = "Nikkei 225"
            elif target_type == 'n400': base_msg = "Nikkei 400 (Excl)"
            
            jp_screener_manager.update_message(f"Scanning {base_msg} stocks...")
            
            # 비동기 실행
            async def run_screening():
                signals_n225 = []
                signals_n400 = []
                
                async with JPXCollector() as collector:
                    async with YahooJapanNewsCollector() as news_collector:
                        # JPX Nikkei 400 전체 종목 대상
                        # Always get full list first (optimized in collector)
                        gainers = await collector.get_top_gainers(top_n=400)
                        
                        # Filter based on run_type
                        filtered_gainers = []
                        for g in gainers:
                            g_code = g.code
                            if not g_code.endswith('.T'):
                                g_code = f"{g_code}.T"
                            
                            is_n225 = g_code in n225_codes
                            
                            if target_type == 'all':
                                filtered_gainers.append(g)
                            elif target_type == 'n225' and is_n225:
                                filtered_gainers.append(g)
                            elif target_type == 'n400' and not is_n225:
                                filtered_gainers.append(g)
                        
                        jp_screener_manager.update_message(f"Found {len(filtered_gainers)} candidates for {target_type}, analyzing...")
                        
                        config = JPSignalConfig()
                        scorer = Scorer()
                        
                        # --- 병렬 분석 함수 ---
                        async def analyze_single_stock(stock):
                            try:
                                # 차트 데이터 (60일치)
                                charts = await collector.get_chart_data(stock.code, days=60)
                                if not charts or len(charts) < 20:
                                    return None
                                
                                # 수급 데이터 (Zero for JP currently)
                                supply = await collector.get_supply_data(stock.code)
                                
                                # 1차 점수 계산 (뉴스 없이) - 성능 최적화
                                prelim_score, _ = scorer.calculate(stock, charts, [], supply)
                                
                                news = []
                                # 1차 점수가 양호한 경우에만 뉴스 수집 (네트워크 병목 해소)
                                # 기준: 4.0점 이상 (B급 진입 가능성)
                                if prelim_score.total >= 4.0:
                                    try:
                                        # 뉴스 데이터 (Timeout 적용됨)
                                        news = await news_collector.get_stock_news(
                                            code=stock.code, 
                                            limit=3, 
                                            stock_name=stock.name
                                        )
                                    except Exception:
                                        news = []
                                
                                # 최종 점수 계산 (뉴스 포함/미포함)
                                score, checklist = scorer.calculate(stock, charts, news, supply)
                                grade = scorer.determine_grade(stock, score)
                                
                                if grade.value in ['S', 'A', 'B']:
                                    target_pct = {'S': 0.08, 'A': 0.05, 'B': 0.03}.get(grade.value, 0.03)
                                    target_price = round(stock.close * (1 + target_pct))
                                    
                                    # Result Dict
                                    return {
                                        'code': stock.code,
                                        'name': stock.name,
                                        'sector': stock.sector,
                                        'market': 'TSE',
                                        'close': stock.close,
                                        'change_pct': stock.change_pct,
                                        'grade': grade.value,
                                        'score': score.total, # Float now
                                        'target_price': target_price,
                                        'score_detail': {
                                            'news': score.news,
                                            'volume': score.volume,
                                            'chart': score.chart,
                                            'candle': score.candle,
                                            'consolidation': score.consolidation,
                                            'supply': score.supply,
                                            'technical': score.technical,
                                        },
                                        'news': [{'title': n.title, 'source': n.source} for n in news[:3]],
                                    }
                                return None
                            except Exception as e:
                                print(f"Error analyzing {stock.code}: {e}")
                                return None

                        # --- 배치 병렬 처리 ---
                        batch_size = 20
                        
                        for i in range(0, len(filtered_gainers), batch_size):
                            batch = filtered_gainers[i:i+batch_size]
                            
                            progress = min(100, int((i / len(filtered_gainers)) * 100))
                            jp_screener_manager.update_message(f"Analyzing {target_type}... {progress}% ({i}/{len(filtered_gainers)})")
                            
                            tasks = [analyze_single_stock(stock) for stock in batch]
                            results = await asyncio.gather(*tasks)
                            
                            for res in results:
                                if res:
                                    # Split logic for correct list
                                    code_clean = res['code']
                                    code_full = f"{code_clean}.T"
                                    
                                    if code_full in n225_codes:
                                        signals_n225.append(res)
                                    else:
                                        signals_n400.append(res)
                            
                            await asyncio.sleep(0.5)
                
                return signals_n225, signals_n400, len(filtered_gainers)
            
            signals_n225, signals_n400, total_scanned_count = asyncio.run(run_screening())
            
            # --- Result Finalization (Top 30 Limit) ---
            def finalize_signals(sig_list, filename_prefix, total_count_val):
                 # Sort by Grade (S->A->B) then Score (Desc)
                 grade_map = {'S': 3, 'A': 2, 'B': 1, 'C': 0}
                 sorted_list = sorted(sig_list, key=lambda x: (grade_map.get(x['grade'], 0), x['score']), reverse=True)
                 
                 # Limit to Top 30
                 final_list = sorted_list[:30]
                 
                 result_data = {
                    "generated_at": datetime.now().isoformat(),
                    "filtered_count": len(final_list),
                    "total_scanned": total_count_val,
                    "signals": final_list
                 }
                 
                 # Save Files
                 with open(os.path.join(data_dir, f'{filename_prefix}latest.json'), 'w', encoding='utf-8') as f:
                     json.dump(result_data, f, ensure_ascii=False, indent=2)
                 
                 today_str = date.today().strftime('%Y%m%d')
                 with open(os.path.join(data_dir, f'{filename_prefix}results_{today_str}.json'), 'w', encoding='utf-8') as f:
                     json.dump(result_data, f, ensure_ascii=False, indent=2)
                     
                 return len(final_list)

            msg_parts = []
            
            if target_type in ['all', 'n225']:
                count_n225 = finalize_signals(signals_n225, 'jongga_v2_n225_', total_scanned_count)
                msg_parts.append(f"N225: {count_n225}/{total_scanned_count}")
                
            if target_type in ['all', 'n400']:
                count_n400 = finalize_signals(signals_n400, 'jongga_v2_n400_', total_scanned_count)
                msg_parts.append(f"Others: {count_n400}/{total_scanned_count}")
            
            jp_screener_manager.stop(f"Completed. {', '.join(msg_parts)}")
            
        except Exception as e:
            print(f"Error running JP screener: {e}")
            traceback.print_exc()
            jp_screener_manager.stop(f"Error: {str(e)}")

    thread = threading.Thread(target=_run_task, args=(run_type,))
    thread.start()

    return jsonify({
        "status": "accepted",
        "message": f"JP Screening ({run_type}) started in background"
    }), 202


# === 백테스트 요약 ===
@jp_bp.route('/backtest-summary')
def get_backtest_summary():
    """백테스트 요약"""
    try:
        summary = {
            'closing_bet': {'status': 'No Data', 'win_rate': 0, 'avg_return': 0, 'count': 0}
        }
        
        data_dir = get_jp_data_dir()
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


# === 실시간 가격 ===
@jp_bp.route('/realtime-prices', methods=['POST'])
def get_realtime_prices():
    """실시간 가격 조회 (yfinance Batch)"""
    try:
        data = request.get_json()
        tickers = data.get('tickers', [])
        
        if not tickers:
            return jsonify({})
        
        # 티커 변환 (.T 접미사)
        valid_tickers = []
        ticker_map = {}
        
        for t in tickers:
            if not t.endswith('.T'):
                symbol = f"{t}.T"
            else:
                symbol = t
            valid_tickers.append(symbol)
            ticker_map[symbol] = t
        
        # Batch Download
        df = yf.download(valid_tickers, period="1d", group_by='ticker', progress=False)
        
        prices = {}
        
        if df.empty:
            return jsonify({})
        
        if len(valid_tickers) == 1:
            symbol = valid_tickers[0]
            try:
                if isinstance(df.columns, pd.MultiIndex):
                    series = df[symbol]['Close'] if symbol in df.columns.levels[0] else None
                else:
                    series = df['Close']
                
                if series is not None and not series.dropna().empty:
                    prices[ticker_map[symbol]] = float(series.dropna().iloc[-1])
            except:
                pass
        else:
            for symbol in valid_tickers:
                try:
                    if isinstance(df.columns, pd.MultiIndex) and symbol in df.columns.levels[0]:
                        series = df[symbol]['Close']
                        if not series.dropna().empty:
                            prices[ticker_map[symbol]] = float(series.dropna().iloc[-1])
                except:
                    continue
        
        return jsonify(prices)
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# === 성과 분석 ===
@jp_bp.route('/performance/analyze', methods=['POST'])
def analyze_performance():
    """성과 분석 (과거 포착 종목의 이후 주가 추적)"""
    try:
        req_data = request.get_json()
        target_date_str = req_data.get('date')  # 2026-01-20
        target_type = req_data.get('type', 'n225') # n225 | n400
        
        if not target_date_str:
            return jsonify({'error': 'Date is required'}), 400
            
        # load signal data (Support both N225 and N400 files)
        data_dir = get_jp_data_dir()
        date_nohol = target_date_str.replace('-', '')
        
        # Files to check based on type
        files_to_check = []
        
        if target_type == 'n225':
            files_to_check.append(f"jongga_v2_n225_results_{date_nohol}.json")
            files_to_check.append(f"jongga_v2_results_{date_nohol}.json") # Legacy fallback
        elif target_type == 'n400':
            files_to_check.append(f"jongga_v2_n400_results_{date_nohol}.json")
        else:
            # Fallback or 'all'
            files_to_check.append(f"jongga_v2_n225_results_{date_nohol}.json")
            files_to_check.append(f"jongga_v2_n400_results_{date_nohol}.json")
            files_to_check.append(f"jongga_v2_results_{date_nohol}.json")
        
        signals = []
        found_any = False
        
        for filename in files_to_check:
            file_path = os.path.join(data_dir, filename)
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        signal_data = json.load(f)
                        signals = signal_data.get('signals', [])
                        if signals:
                            found_any = True
                            break # Use the first found file in priority list
                except:
                    continue
        
        if not found_any:
            return jsonify({'error': f'Data not found for {target_date_str}'}), 404

        if not signals:
            return jsonify({'dates': [], 'rows': []})
        
        # Collect tickers (JP uses .T suffix)
        tickers = []
        ticker_map = {}  # symbol -> signal object
        
        for s in signals:
            code = s.get('code') or s.get('ticker')
            if not code:
                continue
            
            # JP market uses .T suffix
            code_clean = code.replace('.T', '')
            symbol = f"{code_clean}.T"
            tickers.append(symbol)
            ticker_map[symbol] = s
            ticker_map[code_clean] = s
            
        if not tickers:
            return jsonify({'dates': [], 'rows': []})
             
        # Fetch History
        print(f"[JP] Analyzing performance for {target_date_str}. Tickers: {len(tickers)}")
        
        # Download
        df = yf.download(tickers, start=target_date_str, group_by='ticker', progress=False, threads=False)
        
        if df.empty:
            return jsonify({'dates': [], 'rows': []})
             
        # Extract dates
        market_dates = [d.strftime('%Y-%m-%d') for d in df.index]
        
        # Build Rows
        rows = []
        is_multi = len(tickers) > 1
        
        for symbol in tickers:
            s = ticker_map.get(symbol)
            if not s:
                continue
            
            # Convert signal to match KR format expected by frontend
            signal_info = {
                'stock_code': s.get('code', ''),
                'stock_name': s.get('name', ''),
                'grade': s.get('grade', 'C'),
                'score': s.get('score', 0),
                'current_price': s.get('close', 0),
                'entry_price': s.get('close', 0),
                'market': 'TSE'
            }
            
            row = {
                'signal_info': signal_info,
                'daily_stats': []
            }
            
            try:
                # Get close series
                series = None
                if is_multi:
                    if isinstance(df.columns, pd.MultiIndex):
                        if symbol in df.columns.levels[0]:
                            series = df[symbol]['Close']
                else:
                    if isinstance(df.columns, pd.MultiIndex):
                        if symbol in df.columns.levels[0]:
                            series = df[symbol]['Close']
                        else:
                            series = df['Close']
                    else:
                        series = df['Close']
                        
                if series is not None:
                    entry_price = s.get('close', 0)
                    
                    for date_val in df.index:
                        d_str = date_val.strftime('%Y-%m-%d')
                        if d_str not in market_dates:
                            continue
                        
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
                print(f"Error processing {symbol}: {e}")
                pass
                
            rows.append(row)
            
        return jsonify({
            'dates': market_dates,
            'rows': rows
        })
        
    except Exception as e:
        print("JP Analysis Error:", e)
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@jp_bp.route('/chart/<code>')
def get_jp_chart(code):
    """특정 종목의 차트 데이터 조회"""
    try:
        import asyncio
        from engine.jp_collectors import JPXCollector
        
        async def _fetch():
            async with JPXCollector() as collector:
                return await collector.get_chart_data(code, days=180) # Support 6 months
        
        charts = asyncio.run(_fetch())
        
        # JSON 직렬화 가능한 형태로 변환
        result = []
        for c in charts:
            result.append({
                'date': str(c.date),
                'open': c.open,
                'high': c.high,
                'low': c.low,
                'close': c.close,
                'volume': c.volume
            })
        
        return jsonify(result)
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# === VCP 시그널 ===
@jp_bp.route('/vcp/latest')
def get_jp_vcp_latest():
    """JP VCP 최신 시그널 조회"""
    try:
        data_dir = get_jp_data_dir()
        vcp_path = os.path.join(data_dir, 'vcp_latest.json')
        
        if os.path.exists(vcp_path):
            with open(vcp_path, 'r', encoding='utf-8') as f:
                return jsonify(json.load(f))
        
        return jsonify({
            "signals": [],
            "total_count": 0,
            "message": "VCP 데이터가 없습니다. 스크리너를 실행하세요."
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@jp_bp.route('/vcp/dates', methods=['GET'])
def get_vcp_dates():
    """VCP 데이터가 존재하는 날짜 목록"""
    try:
        data_dir = get_jp_data_dir()
        files = glob.glob(os.path.join(data_dir, 'vcp_*.json'))
        
        dates = []
        for f in files:
            basename = os.path.basename(f)
            if basename.startswith('vcp_') and basename != 'vcp_latest.json':
                date_part = basename[4:12] # vcp_YYYYMMDD.json
                if len(date_part) == 8 and date_part.isdigit():
                    formatted = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:]}"
                    dates.append(formatted)
        
        dates.sort(reverse=True)
        return jsonify(dates)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@jp_bp.route('/vcp/history/<date_str>', methods=['GET'])
def get_vcp_history(date_str):
    """특정 날짜의 VCP 결과"""
    try:
        data_dir = get_jp_data_dir()
        if '-' in date_str:
            date_str = date_str.replace('-', '')
        
        filename = f"vcp_{date_str}.json"
        file_path = os.path.join(data_dir, filename)
        
        if not os.path.exists(file_path):
            return jsonify({"error": "Data not found"}), 404
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@jp_bp.route('/vcp/run', methods=['POST'])
def run_jp_vcp():
    """JP VCP 스크리너 실행 (Background)"""
    if not jp_screener_manager.start('VCP'):
        return jsonify({"status": "error", "message": "Already running"}), 409

    def _run_task():
        try:
            import asyncio
            from engine.jp_vcp import JPVCPScreener
            
            jp_screener_manager.update_message("Scanning Nikkei 225/400 signals for VCP patterns & Supply...")
            screener = JPVCPScreener()
            result = asyncio.run(screener.run_vcp_scan())
            
            if "status" in result and result["status"] == "error":
                jp_screener_manager.stop(f"Error: {result['message']}")
            else:
                jp_screener_manager.stop(f"VCP Scan Completed. Found {result.get('total_count', 0)} signals.")
        except Exception as e:
            traceback.print_exc()
            jp_screener_manager.stop(f"Error: {str(e)}")

    thread = threading.Thread(target=_run_task)
    thread.start()

    return jsonify({
        "status": "accepted",
        "message": "JP VCP check started in background"
    }), 202
