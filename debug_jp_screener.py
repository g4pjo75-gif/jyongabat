
import asyncio
import sys
import os
from engine.jp_collectors import JPXCollector, YahooJapanNewsCollector
from engine.jp_config import JPSignalConfig
from engine.scorer import Scorer
from datetime import datetime

# 콘솔에 한글 출력 설정 (Windows)
sys.stdout.reconfigure(encoding='utf-8')

async def debug_screening():
    print("=== JP Screener Debug Start ===")
    
    async with JPXCollector() as collector:
        async with YahooJapanNewsCollector() as news_collector:
            print("[1] Fetching top gainers (top_n=400)...")
            gainers = await collector.get_top_gainers(top_n=400)
            print(f" -> Found {len(gainers)} stocks.")
            
            if not gainers:
                print("No stocks found. Check network or filter settings.")
                return

            print("[2] Starting parallel analysis...")
            config = JPSignalConfig()
            scorer = Scorer()
            signals = []
            
            async def analyze_single_stock(stock):
                try:
                    # 차트 데이터 reduced days to speed up debug
                    charts = await collector.get_chart_data(stock.code, days=30)
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
                    
                    # Debug: print scores
                    # print(f" {stock.name}: {grade.value} ({score.total})")

                    if grade.value in ['S', 'A', 'B']:
                         return {
                            'code': stock.code,
                            'name': stock.name,
                            'grade': grade.value
                        }
                    return None
                except Exception as e:
                    print(f"Error analyzing {stock.code}: {e}")
                    return None

            # 배치 처리 테스트 (Batch size 10)
            batch_size = 10
            total_items = len(gainers)
            # Limit total items for debug speed (analyzing 20 items only)
            # gainers = gainers[:20] 
            
            for i in range(0, len(gainers), batch_size):
                batch = gainers[i:i+batch_size]
                print(f" Processing batch {i}~{i+len(batch)}...")
                
                tasks = [analyze_single_stock(stock) for stock in batch]
                results = await asyncio.gather(*tasks)
                
                for res in results:
                    if res:
                        signals.append(res)
                
                await asyncio.sleep(0.5)
            
            print(f"=== Debug Completed. Found {len(signals)} signals. Total Scanned: {total_items} ===")

if __name__ == "__main__":
    asyncio.run(debug_screening())
