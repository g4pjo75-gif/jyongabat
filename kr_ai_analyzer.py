#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KR AI Analyzer - GPT + Gemini 듀얼 AI 분석기
"""

import os
import json
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()


@dataclass
class AIRecommendation:
    """AI 추천 결과"""
    action: str  # BUY, HOLD, SELL
    confidence: int  # 0-100
    reason: str


@dataclass
class StockAnalysis:
    """종목 분석 결과"""
    ticker: str
    name: str
    score: float
    fundamentals: Dict[str, Any]
    news: List[Dict]
    gemini_recommendation: Optional[AIRecommendation] = None
    
    def to_dict(self) -> Dict:
        result = asdict(self)
        return result


class KrAiAnalyzer:
    """한국 주식 AI 분석기 (Gemini 전용)"""
    
    def __init__(self):
        self.google_api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        
        self.gemini_model = None
        
        # Gemini 초기화
        # Quota 문제로 인해 비활성화
        print("  [Gemini] Analysis disabled (Quota limits)")
        # if self.google_api_key:
        #     try:
        #         import google.generativeai as genai
        #         genai.configure(api_key=self.google_api_key)
        #         model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
        #         self.gemini_model = genai.GenerativeModel(model_name)
        #         print(f"  Gemini 초기화 완료 ({model_name})")
        #     except Exception as e:
        #         print(f"  Gemini 초기화 실패: {e}")
    
    async def analyze_stock(self, ticker: str, name: str = None, data: Dict = None) -> StockAnalysis:
        """단일 종목 분석"""
        from pykrx import stock
        
        # 기본 정보 조회
        if not name:
            name = stock.get_market_ticker_name(ticker)
        
        # 펀더멘털 조회
        fundamentals = self._get_fundamentals(ticker)
        
        # 뉴스 수집
        news = await self._collect_news(ticker, name)
        
        # Gemini 분석
        gemini_rec = None
        if self.gemini_model:
            gemini_rec = await self._analyze_with_gemini(ticker, name, fundamentals, news, data)
        
        return StockAnalysis(
            ticker=ticker,
            name=name,
            score=data.get('score', 0) if data else 0,
            fundamentals=fundamentals,
            news=news,
            gemini_recommendation=gemini_rec
        )
    
    def _get_fundamentals(self, ticker: str) -> Dict[str, Any]:
        """펀더멘털 데이터 조회"""
        try:
            from pykrx import stock
            
            today = datetime.now().strftime("%Y%m%d")
            
            # 기본 정보
            fund = stock.get_market_cap_by_ticker(today)
            if ticker in fund.index:
                marcap = int(fund.loc[ticker, '시가총액'])
            else:
                marcap = 0
            
            return {
                "marcap": f"{marcap / 100_000_000:,.0f}억원",
                "per": "N/A",
                "pbr": "N/A",
                "roe": "N/A",
                "div_yield": "N/A"
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    async def _collect_news(self, ticker: str, name: str) -> List[Dict]:
        """뉴스 수집"""
        news = []
        
        try:
            import aiohttp
            from bs4 import BeautifulSoup
            
            # 네이버 금융 뉴스
            url = f"https://finance.naver.com/item/news.naver?code={ticker}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # 뉴스 항목 파싱
                        items = soup.select('.tb_cont .tit a')[:5]
                        
                        for item in items:
                            title = item.get_text(strip=True)
                            link = item.get('href', '')
                            
                            if title:
                                news.append({
                                    "title": title,
                                    "url": link,
                                    "source": "네이버금융"
                                })
                                
        except Exception as e:
            print(f"뉴스 수집 실패: {e}")
        
        return news
    
    async def _analyze_with_gemini(
        self,
        ticker: str,
        name: str,
        fundamentals: Dict,
        news: List[Dict],
        data: Dict = None
    ) -> Optional[AIRecommendation]:
        """Gemini로 분석"""
        if not self.gemini_model:
            return None
        
        try:
            # 뉴스 텍스트 구성
            news_text = "\n".join([f"- {n['title']}" for n in news[:5]]) if news else "최근 뉴스 없음"
            
            # 점수 정보
            score_info = ""
            if data:
                score_info = f"""
                VCP 점수: {data.get('score', 'N/A')}
                외국인 5일: {data.get('foreign_5d', 0):,}
                기관 5일: {data.get('inst_5d', 0):,}
                """
            
            prompt = f"""
            당신은 한국 주식 전문 분석가입니다. 다음 종목을 분석해주세요.
            
            종목: {name} ({ticker})
            시가총액: {fundamentals.get('marcap', 'N/A')}
            
            {score_info}
            
            최근 뉴스:
            {news_text}
            
            위 정보를 바탕으로 투자 추천을 해주세요.
            
            반드시 아래 JSON 형식으로만 답변하세요:
            {{"action": "BUY/HOLD/SELL", "confidence": 0-100, "reason": "간단한 이유"}}
            """
            
            response = await asyncio.to_thread(
                self.gemini_model.generate_content,
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            
            import re
            text = response.text.strip()
            
            # JSON 파싱
            if "```" in text:
                text = re.sub(r"```json|```", "", text).strip()
            
            result = json.loads(text)
            
            return AIRecommendation(
                action=result.get("action", "HOLD"),
                confidence=result.get("confidence", 50),
                reason=result.get("reason", "")
            )
            
        except Exception as e:
            print(f"Gemini 분석 실패: {e}")
            return None
    
    async def analyze_signals(self, signals: List[Dict], max_count: int = 10) -> Dict:
        """시그널 리스트 분석"""
        print(f"\n🤖 AI 분석 시작 ({len(signals[:max_count])}개 종목)...")
        
        results = []
        
        for i, signal in enumerate(signals[:max_count], 1):
            ticker = signal.get('ticker', signal.get('stock_code', ''))
            name = signal.get('name', signal.get('stock_name', ''))
            
            print(f"  [{i}/{max_count}] {name} ({ticker}) 분석 중...")
            
            try:
                analysis = await self.analyze_stock(ticker, name, signal)
                results.append(analysis.to_dict())
                
                # Rate limit 방지
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"    ❌ 분석 실패: {e}")
        
        # 결과 저장
        output = {
            "signals": results,
            "generated_at": datetime.now().isoformat(),
            "count": len(results)
        }
        
        # 파일 저장
        data_dir = os.path.join(os.path.dirname(__file__), 'data')
        os.makedirs(data_dir, exist_ok=True)
        
        output_path = os.path.join(data_dir, 'kr_ai_analysis.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ AI 분석 완료! {len(results)}개 종목")
        print(f"   저장 위치: {output_path}")
        
        return output


# 테스트용
if __name__ == "__main__":
    analyzer = KrAiAnalyzer()
    
    # 샘플 시그널
    test_signals = [
        {"ticker": "005930", "name": "삼성전자", "score": 75},
        {"ticker": "000660", "name": "SK하이닉스", "score": 70},
    ]
    
    result = asyncio.run(analyzer.analyze_signals(test_signals, max_count=2))
    print(json.dumps(result, ensure_ascii=False, indent=2))
