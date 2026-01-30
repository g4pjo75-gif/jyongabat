"""
시그널 생성기 (Main Engine)
- Collector로부터 데이터 수집
- Scorer로 점수 계산
- PositionSizer로 자금 관리
- 최종 Signal 생성
"""

import asyncio
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict
import time
import sys
import os
import json

# 모듈 경로 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.config import SignalConfig, Grade
from engine.models import (
    StockData, Signal, SignalStatus, 
    ScoreDetail, ChecklistDetail, ScreenerResult
)
from engine.collectors import KRXCollector, EnhancedNewsCollector
from engine.scorer import Scorer
from engine.position_sizer import PositionSizer
from engine.llm_analyzer import LLMAnalyzer


class SignalGenerator:
    """종가베팅 시그널 생성기 (v2)"""
    
    def __init__(
        self,
        config: SignalConfig = None,
        capital: float = 10_000_000,
    ):
        """
        Args:
            capital: 총 자본금 (기본 1천만원)
            config: 설정 (기본 설정 사용)
        """
        self.config = config or SignalConfig()
        self.capital = capital
        
        self.scorer = Scorer(self.config)
        self.position_sizer = PositionSizer(capital, self.config)
        self.llm_analyzer = LLMAnalyzer()  # API Key from env
        
        self._collector: Optional[KRXCollector] = None
        self._news: Optional[EnhancedNewsCollector] = None
    
    async def __aenter__(self):
        self._collector = KRXCollector(self.config)
        await self._collector.__aenter__()
        
        self._news = EnhancedNewsCollector(self.config)
        await self._news.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._collector:
            await self._collector.__aexit__(exc_type, exc_val, exc_tb)
        if self._news:
            await self._news.__aexit__(exc_type, exc_val, exc_tb)
    
    async def generate(
        self,
        target_date: date = None,
        markets: List[str] = None,
        top_n: int = 30,
    ) -> List[Signal]:
        """
        시그널 생성
        
        Args:
            target_date: 대상 날짜 (기본: 오늘)
            markets: 대상 시장 (기본: KOSPI, KOSDAQ)
            top_n: 상승률 상위 N개 종목
        
        Returns:
            Signal 리스트 (등급순 정렬)
        """
        target_date = target_date or date.today()
        markets = markets or ["KOSPI", "KOSDAQ"]
        
        all_signals = []
        
        for market in markets:
            print(f"\n[{market}] Screening top gainers...")
            
            # 1. 상승률 상위 종목 조회
            candidates = await self._collector.get_top_gainers(market, top_n)
            print(f"  - Filter 1 Passed: {len(candidates)}")
            
            # 2. 병렬 분석 준비
            semaphore = asyncio.Semaphore(10)  # 동시 10개 제한
            
            async def _analyze_with_semaphore(stock, total_cnt, current_idx):
                async with semaphore:
                    try:
                        # 진행률 표시 (대략적으로)
                        print(f"  Processing {stock.name}...", end='\r')
                        return await self._analyze_stock(stock, target_date)
                    except Exception as e:
                        print(f"Error processing {stock.name}: {e}")
                        return None

            tasks = [
                _analyze_with_semaphore(stock, len(candidates), i) 
                for i, stock in enumerate(candidates)
            ]
            
            # 병렬 실행
            results = await asyncio.gather(*tasks)
            
            # 유효한 시그널만 필터링
            for signal in results:
                if signal and signal.grade != Grade.C:
                    all_signals.append(signal)
                    print(f"\n    [OK] {signal.stock_name}: Grade {signal.grade.value} Signal created! (Score: {signal.score.total})")
        
        # 3. 등급순 정렬 (S > A > B)
        grade_order = {Grade.S: 0, Grade.A: 1, Grade.B: 2, Grade.C: 3}
        all_signals.sort(key=lambda s: (grade_order[s.grade], -s.score.total))
        
        # 4. 최대 포지션 수 제한
        if len(all_signals) > self.config.max_positions:
            all_signals = all_signals[:self.config.max_positions]
        
        print(f"\nTotal {len(all_signals)} signals created.")
        return all_signals
    
    async def _analyze_stock(
        self,
        stock: StockData,
        target_date: date
    ) -> Optional[Signal]:
        """개별 종목 분석"""
        try:
            # 1. 상세 정보 조회
            detail = await self._collector.get_stock_detail(stock.code)
            if detail:
                stock.high_52w = detail.high_52w
            
            # 2. 차트 데이터 조회
            charts = await self._collector.get_chart_data(stock.code, 60)
            
            # 3. 뉴스 조회
            news_list = await self._news.get_stock_news(stock.code, 3, stock.name)
            
            # 4. LLM 뉴스 분석
            llm_result = None
            if news_list and self.llm_analyzer.is_available():
                # Rate Limit 방지 (병렬 처리 시 각 Task 내 대기시간 축소)
                await asyncio.sleep(0.5) 
                
                print(f"    [LLM] Analyzing {stock.name} news...")
                news_dicts = [{"title": n.title, "summary": n.summary} for n in news_list]
                llm_result = await self.llm_analyzer.analyze_news_sentiment(stock.name, news_dicts)
                if llm_result:
                    print(f"      -> Score: {llm_result.get('score')}")
            
            # 5. 수급 데이터 조회
            supply = await self._collector.get_supply_data(stock.code)
            
            # 6. 점수 계산
            score, checklist = self.scorer.calculate(stock, charts, news_list, supply, llm_result)
            
            # 7. 등급 결정
            grade = self.scorer.determine_grade(stock, score)
            
            # C등급은 제외
            if grade == Grade.C:
                return None
            
            # 8. 포지션 계산
            position = self.position_sizer.calculate(stock.close, grade)
            
            # 9. 시그널 생성
            signal = Signal(
                stock_code=stock.code,
                stock_name=stock.name,
                market=stock.market,
                sector=stock.sector,
                signal_date=target_date,
                signal_time=datetime.now(),
                grade=grade,
                score=score,
                checklist=checklist,
                news_items=[{
                    "title": n.title,
                    "source": n.source,
                    "published_at": n.published_at.isoformat() if n.published_at else "",
                    "url": n.url
                } for n in news_list[:5]],
                current_price=stock.close,
                entry_price=position.entry_price,
                stop_price=position.stop_price,
                target_price=position.target_price,
                r_value=position.r_value,
                position_size=position.position_size,
                quantity=position.quantity,
                r_multiplier=position.r_multiplier,
                trading_value=stock.trading_value,
                change_pct=stock.change_pct,
                status=SignalStatus.PENDING,
                created_at=datetime.now(),
            )
            
            return signal
            
        except Exception as e:
            print(f"    Analysis failed: {e}")
            return None
    
    def get_summary(self, signals: List[Signal]) -> Dict:
        """시그널 요약 정보"""
        summary = {
            "total": len(signals),
            "by_grade": {g.value: 0 for g in Grade},
            "by_market": {},
            "total_position": 0,
            "total_risk": 0,
        }
        
        for s in signals:
            summary["by_grade"][s.grade.value] += 1
            summary["by_market"][s.market] = summary["by_market"].get(s.market, 0) + 1
            summary["total_position"] += s.position_size
            summary["total_risk"] += s.r_value * s.r_multiplier
        
        return summary


async def run_screener(
    capital: float = 50_000_000,
    markets: List[str] = None,
) -> ScreenerResult:
    """스크리너 실행 (간편 함수)"""
    start_time = time.time()
    
    async with SignalGenerator(capital=capital) as generator:
        signals = await generator.generate(markets=markets)
        summary = generator.get_summary(signals)
    
    processing_time = (time.time() - start_time) * 1000
    
    result = ScreenerResult(
        date=date.today(),
        total_candidates=summary["total"],
        filtered_count=len(signals),
        signals=signals,
        by_grade=summary["by_grade"],
        by_market=summary["by_market"],
        processing_time_ms=processing_time,
    )
    
    # 결과 저장
    save_result_to_json(result)
    
    return result


def save_result_to_json(result: ScreenerResult):
    """결과 JSON 저장 (Daily + Latest)"""
    data = {
        "date": result.date.isoformat(),
        "total_candidates": result.total_candidates,
        "filtered_count": result.filtered_count,
        "signals": [s.to_dict() for s in result.signals],
        "by_grade": result.by_grade,
        "by_market": result.by_market,
        "processing_time_ms": result.processing_time_ms,
        "updated_at": datetime.now().isoformat()
    }
    
    # 1. 날짜별 파일 저장
    date_str = result.date.strftime("%Y%m%d")
    filename = f"jongga_v2_results_{date_str}.json"
    
    base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    os.makedirs(base_dir, exist_ok=True)
    
    save_path = os.path.join(base_dir, filename)
    
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\n[Saved] Daily: {save_path}")
    
    # 2. Latest 파일 업데이트
    latest_path = os.path.join(base_dir, "jongga_v2_latest.json")
    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"[Saved] Latest: {latest_path}")


# 테스트용 메인
async def main():
    """테스트 실행"""
    print("=" * 60)
    print("종가베팅 시그널 생성기 v2")
    print("=" * 60)
    
    capital = 50_000_000
    print(f"\n자본금: {capital:,}원")
    print(f"R값: {capital * 0.005:,.0f}원 (0.5%)")
    
    result = await run_screener(capital=capital)
    
    print(f"\n처리 시간: {result.processing_time_ms:.0f}ms")
    print(f"생성된 시그널: {len(result.signals)}개")
    print(f"등급별: {result.by_grade}")
    
    print("\n" + "=" * 60)
    print("시그널 상세")
    print("=" * 60)
    
    for i, signal in enumerate(result.signals, 1):
        print(f"\n[{i}] {signal.stock_name} ({signal.stock_code})")
        print(f"    등급: {signal.grade.value}")
        print(f"    점수: {signal.score.total}/12")
        print(f"    등락률: {signal.change_pct:+.2f}%")
        print(f"    거래대금: {signal.trading_value / 100_000_000:,.0f}억")
        print(f"    진입가: {signal.entry_price:,}원")
        print(f"    손절가: {signal.stop_price:,}원")
        print(f"    목표가: {signal.target_price:,}원")



if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n중단됨")


async def analyze_single_stock_by_code(
    code: str,
    capital: float = 50_000_000,
) -> Optional[Signal]:
    """
    단일 종목 재분석 및 결과 JSON 업데이트
    
    Args:
        code: 종목 코드 (예: "005930")
        capital: 자본금
        
    Returns:
        재분석된 Signal 또는 None
    """
    async with SignalGenerator(capital=capital) as generator:
        # 1. 최신 JSON 로드 (이전 데이터 기반)
        base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
        latest_path = os.path.join(base_dir, "jongga_v2_latest.json")
        
        if not os.path.exists(latest_path):
            print("Latest data file not found.")
            return None
            
        with open(latest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        target_signal_data = next((s for s in data["signals"] if s["stock_code"] == code), None)
        
        if not target_signal_data:
            print("Signal not found in latest data. Cannot re-analyze without base info.")
            return None
            
        # StockData 복원
        stock = StockData(
            code=target_signal_data.get("stock_code", code),
            name=target_signal_data.get("stock_name", ""),
            market=target_signal_data.get("market", "KOSPI"),
            sector=target_signal_data.get("sector", ""),
            close=target_signal_data.get("current_price", target_signal_data.get("entry_price", 0)),
            change_pct=target_signal_data.get("change_pct", 0),
            trading_value=target_signal_data.get("trading_value", 0),
            volume=0, 
            marcap=0  
        )
        
        # 2. 재분석 실행
        print(f"Re-analyzing {stock.name} ({stock.code})...")
        new_signal = await generator._analyze_stock(stock, date.today())
        
        if new_signal:
            print(f"[OK] Re-analysis complete: {new_signal.grade.value} (Score: {new_signal.score.total})")
            
            # 3. JSON 데이터 업데이트 및 저장
            updated_signals = [
                new_signal.to_dict() if s["stock_code"] == code else s 
                for s in data["signals"]
            ]
            
            data["signals"] = updated_signals
            data["updated_at"] = datetime.now().isoformat()
            
            # 파일 저장 - Latest
            with open(latest_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            # 파일 저장 - Daily
            date_str = date.today().strftime("%Y%m%d")
            daily_path = os.path.join(base_dir, f"jongga_v2_results_{date_str}.json")
            if os.path.exists(daily_path):
                with open(daily_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            
            return new_signal
            
        else:
            print("Re-analysis failed or grade too low.")
            return None
