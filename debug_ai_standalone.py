import asyncio
import os
import sys

# Set path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from engine.collectors import EnhancedNewsCollector
from engine.llm_analyzer import LLMAnalyzer
from engine.config import SignalConfig

async def test_ai_analysis():
    print("Testing AI Analysis components...")
    
    config = SignalConfig()
    analyzer = LLMAnalyzer()
    
    # Test Data: Samsung Electronics
    ticker = "005930"
    name = "삼성전자"
    
    print(f"1. Collecting news for {name} ({ticker})...")
    async with EnhancedNewsCollector(config) as news_collector:
        news_list = await news_collector.get_stock_news(ticker, 3, name)
        
        if not news_list:
            print("❌ No news found.")
            return

        print(f"✅ Found {len(news_list)} news items.")
        news_dicts = [{"title": n.title, "summary": n.summary} for n in news_list]
        
        print("2. Running LLM Analysis...")
        ai_result = await analyzer.analyze_news_sentiment(name, news_dicts)
        
        if ai_result:
            print("✅ Analysis Result:")
            print(ai_result)
        else:
            print("❌ LLM Analysis returned None.")

if __name__ == "__main__":
    try:
        asyncio.run(test_ai_analysis())
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
