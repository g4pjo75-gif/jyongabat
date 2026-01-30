
import asyncio
import sys
import os
import json
from datetime import datetime, date
from engine.jp_collectors import JPXCollector, YahooJapanNewsCollector
from engine.jp_config import JPSignalConfig
from engine.scorer import Scorer

# 콘솔에 한글 출력 설정
sys.stdout.reconfigure(encoding='utf-8')

def get_data_dir():
    # 현재 위치: d:\Programs\Antigravity\work\jyongabat2
    # data dir: d:\Programs\Antigravity\work\jyongabat2\data\jp
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, 'data', 'jp')
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    return data_dir

async def run_screening_manual():
    print("=== JP Screener Manual Run Start ===")
    start_time = datetime.now()
    
    async with JPXCollector() as collector:
        async with YahooJapanNewsCollector() as news_collector:
            print("[1] Fetching top gainers (top_n=400)...")
            gainers = await collector.get_top_gainers(top_n=400)
            print(f" -> Found {len(gainers)} stocks.")
            
            if not gainers:
                print("No stocks found.")
                return

            print(f"[2] Starting parallel analysis (Batch Processing)...")
            config = JPSignalConfig()
            scorer = Scorer()
            signals = []
            
            async def analyze_single_stock(stock):
                try:
                    # 차트 데이터 (60일치)
                    charts = await collector.get_chart_data(stock.code, days=60)
                    if not charts or len(charts) < 20:
                        return None
                    
                    # 뉴스 데이터
                    news = await news_collector.get_stock_news(
                        code=stock.code, 
                        limit=3, 
                        stock_name=stock.name
                    )
                    
                    # 수급 데이터
                    supply = await collector.get_supply_data(stock.code)
                    
                    # 점수 계산
                    score, checklist = scorer.calculate(stock, charts, news, supply)
                    grade = scorer.determine_grade(stock, score)
                    
                    # 등급 필터링 (S/A/B)
                    if grade.value in ['S', 'A', 'B']:
                        target_pct = {'S': 0.08, 'A': 0.05, 'B': 0.03}.get(grade.value, 0.03)
                        target_price = round(stock.close * (1 + target_pct))
                        
                        return {
                            'code': stock.code,
                            'name': stock.name,
                            'sector': stock.sector,
                            'market': 'TSE',
                            'close': stock.close,
                            'change_pct': stock.change_pct,
                            'grade': grade.value,
                            'score': score.total,
                            'target_price': target_price,
                            'score_detail': {
                                'news': score.news,
                                'volume': score.volume,
                                'chart': score.chart,
                                'candle': score.candle,
                                'consolidation': score.consolidation,
                                'supply': score.supply,
                            },
                        }
                    return None
                except Exception as e:
                    # print(f"Error analyzing {stock.code}: {e}")
                    return None

            batch_size = 20
            for i in range(0, len(gainers), batch_size):
                batch = gainers[i:i+batch_size]
                progress = int((i / len(gainers)) * 100)
                print(f" Analyzing... {progress}% ({i}/{len(gainers)})")
                
                tasks = [analyze_single_stock(stock) for stock in batch]
                results = await asyncio.gather(*tasks)
                
                for res in results:
                    if res:
                        signals.append(res)
                
                await asyncio.sleep(0.5)
            
            print(f"Analysis Completed. Found {len(signals)} valid signals.")
            
            # Save results
            result_data = {
                "generated_at": datetime.now().isoformat(),
                "filtered_count": len(signals),
                "total_scanned": len(gainers),  # This field will solve the issue
                "signals": sorted(signals, key=lambda x: (-ord(x['grade']), -x['score']))
            }
            
            data_dir = get_data_dir()
            
            # Save latest
            with open(os.path.join(data_dir, 'jongga_v2_latest.json'), 'w', encoding='utf-8') as f:
                json.dump(result_data, f, ensure_ascii=False, indent=2)
            
            # Save history
            today_str = date.today().strftime('%Y%m%d')
            with open(os.path.join(data_dir, f'jongga_v2_results_{today_str}.json'), 'w', encoding='utf-8') as f:
                json.dump(result_data, f, ensure_ascii=False, indent=2)
                
            print(f"Results saved to {data_dir}")

if __name__ == "__main__":
    asyncio.run(run_screening_manual())
