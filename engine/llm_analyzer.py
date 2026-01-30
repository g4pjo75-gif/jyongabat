"""
LLM 기반 뉴스 분석기 (Gemini)
"""

import os
import asyncio
from typing import List, Dict, Optional
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()


class LLMAnalyzer:
    """Gemini를 이용한 뉴스 분석 및 점수 산출"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.model = None
        
        # Quota 문제로 인해 비활성화
        print("[LLM] Gemini analysis is disabled due to quota limits.")
        self.model = None
        
        # if not self.api_key:
        #     print("Warning: GOOGLE_API_KEY not found. LLM analysis will be skipped.")
        # else:
        #     try:
        #         import google.generativeai as genai
        #         genai.configure(api_key=self.api_key)
        #         
        #         # 모델명 환경변수에서 로드 (기본값: gemini-2.0-flash-exp)
        #         model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
        #         self.model = genai.GenerativeModel(model_name)
        #         print(f"[LLM] Gemini 초기화 완료: {model_name}")
        #     except Exception as e:
        #         print(f"[LLM] Gemini 초기화 실패: {e}")
        #         self.model = None
    
    async def analyze_news_sentiment(
        self, 
        stock_name: str, 
        news_items: List[Dict]
    ) -> Dict:
        """
        뉴스 목록을 분석하여 호재 점수(0~3)와 요약 반환
        
        Args:
            stock_name: 종목명
            news_items: [{"title": "...", "summary": "..."}]
            
        Returns:
            {"score": 2, "reason": "종합적인 요약 이유"}
        """
        if not self.model or not news_items:
            return {"score": 0, "reason": "No LLM or No News"}
        
        # 프롬프트 구성
        news_text = ""
        for i, news in enumerate(news_items, 1):
            title = news.get("title", "")
            summary = news.get("summary", "")[:200]  # 너무 길면 자름
            news_text += f"[{i}] 제목: {title}\n내용: {summary}\n\n"
        
        prompt = f"""
당신은 주식 투자 전문가입니다. 다음은 '{stock_name}' 종목에 대한 최신 뉴스들입니다.
이 뉴스들을 **종합적으로 분석**하여 현재 시점에서의 호재 강도를 0~3점으로 평가하세요.

[뉴스 목록]
{news_text}

[점수 기준]
3점: 확실한 호재 (대규모 수주, 상한가 재료, 어닝 서프라이즈, 경영권 분쟁 등)
2점: 긍정적 호재 (실적 개선, 기대감, 테마 상승)
1점: 단순/중립적 소식
0점: 악재 또는 별다른 호재 없음

[출력 형식]
뉴스 3개를 따로 평가하지 말고, **종목 전체에 대한 하나의 평가**를 내리세요.
반드시 아래 포맷의 **단일 JSON 객체**로만 답하세요. (Markdown code block 없이)

Format: {{"score": 2, "reason": "종합적인 요약 이유"}}
"""
        
        try:
            # 비동기 실행
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            
            import json
            import re
            
            text = response.text.strip()
            
            # JSON 추출 (Markdown 코드블록 제거 및 정규식)
            if "```" in text:
                text = re.sub(r"```json|```", "", text).strip()
            
            # 중괄호로 시작하고 끝나는지 확인
            if not (text.startswith("{") and text.endswith("}")):
                match = re.search(r"\{.*\}", text, re.DOTALL)
                if match:
                    text = match.group()
            
            try:
                result = json.loads(text)
                return result
            except json.JSONDecodeError:
                print(f"[LLM Error] JSON Decode Failed. Raw text: {text[:100]}...")
                return {"score": 0, "reason": "JSON Parsing Failed"}
            
        except Exception as e:
            print(f"[LLM Error] API Call Failed: {e}")
            return {"score": 0, "reason": f"Error: {str(e)}"}
    
    def is_available(self) -> bool:
        """LLM 사용 가능 여부"""
        return self.model is not None
