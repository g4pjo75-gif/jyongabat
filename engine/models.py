"""
종가베팅 엔진 - 데이터 모델
"""

from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from typing import List, Optional, Dict
from enum import Enum


class SignalStatus(Enum):
    """시그널 상태"""
    PENDING = "pending"      # 대기 (당일 생성)
    ACTIVE = "active"        # 진입 완료
    CLOSED = "closed"        # 청산 완료
    EXPIRED = "expired"      # 만료


@dataclass
class StockData:
    """종목 기본 데이터"""
    code: str               # 종목코드
    name: str               # 종목명
    market: str             # KOSPI / KOSDAQ
    sector: str = ""        # 섹터
    close: float = 0        # 종가
    change_pct: float = 0   # 등락률 (%)
    volume: int = 0         # 거래량
    trading_value: int = 0  # 거래대금
    marcap: int = 0         # 시가총액
    high_52w: float = 0     # 52주 고가


@dataclass
class ChartData:
    """일봉 차트 데이터"""
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass
class SupplyData:
    """수급 데이터"""
    code: str
    foreign_buy_5d: int = 0     # 외인 5일 순매수
    foreign_buy_20d: int = 0    # 외인 20일 순매수
    inst_buy_5d: int = 0        # 기관 5일 순매수
    inst_buy_20d: int = 0       # 기관 20일 순매수
    foreign_holding_pct: float = 0.0  # 외인 보유율


@dataclass
class NewsItem:
    """뉴스 아이템"""
    title: str
    summary: str = ""
    source: str = ""
    url: str = ""
    published_at: Optional[datetime] = None
    reliability: float = 0.5    # 신뢰도 (0~1)


@dataclass
class ScoreDetail:
    """점수 상세"""
    news: int = 0           # 뉴스/재료 (0-3)
    volume: int = 0         # 거래대금 (0-3)
    chart: int = 0          # 차트패턴 (0-2)
    candle: int = 0         # 캔들형태 (0-1)
    consolidation: int = 0  # 기간조정 (0-1)
    supply: int = 0         # 수급 (0-2)
    llm_reason: str = ""    # LLM 분석 이유
    
    @property
    def total(self) -> int:
        return self.news + self.volume + self.chart + self.candle + self.consolidation + self.supply
    
    def to_dict(self) -> Dict:
        d = asdict(self)
        d['total'] = self.total
        return d


@dataclass
class ChecklistDetail:
    """체크리스트 상세"""
    has_news: bool = False          # 뉴스/재료 있음
    news_sources: List[str] = field(default_factory=list)  # 뉴스 출처
    is_new_high: bool = False       # 신고가 돌파
    is_breakout: bool = False       # 저항선 돌파
    supply_positive: bool = False   # 수급 양호 (외인+기관)
    volume_surge: bool = False      # 거래량 급증
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class Signal:
    """종가베팅 시그널"""
    stock_code: str
    stock_name: str
    market: str
    sector: str
    signal_date: date
    signal_time: datetime
    
    # 등급 및 점수
    grade: 'Grade'  # S, A, B, C
    score: ScoreDetail
    checklist: ChecklistDetail
    
    # 뉴스
    news_items: List[Dict] = field(default_factory=list)
    
    # 가격 정보
    current_price: float = 0
    entry_price: float = 0
    stop_price: float = 0
    target_price: float = 0
    
    # R값 및 포지션
    r_value: float = 0          # 손절 폭 (원)
    position_size: float = 0    # 투자 금액
    quantity: int = 0           # 수량
    r_multiplier: float = 1.0   # R 배수
    
    # 부가 정보
    trading_value: int = 0      # 거래대금
    change_pct: float = 0       # 등락률
    
    # 상태
    status: SignalStatus = SignalStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            "stock_code": self.stock_code,
            "stock_name": self.stock_name,
            "market": self.market,
            "sector": self.sector,
            "signal_date": self.signal_date.isoformat() if self.signal_date else "",
            "signal_time": self.signal_time.isoformat() if self.signal_time else "",
            "grade": self.grade.value if hasattr(self.grade, 'value') else str(self.grade),
            "score": self.score.to_dict() if hasattr(self.score, 'to_dict') else self.score,
            "checklist": self.checklist.to_dict() if hasattr(self.checklist, 'to_dict') else self.checklist,
            "news_items": self.news_items,
            "current_price": self.current_price,
            "entry_price": self.entry_price,
            "stop_price": self.stop_price,
            "target_price": self.target_price,
            "r_value": self.r_value,
            "position_size": self.position_size,
            "quantity": self.quantity,
            "r_multiplier": self.r_multiplier,
            "trading_value": self.trading_value,
            "change_pct": self.change_pct,
            "status": self.status.value if hasattr(self.status, 'value') else str(self.status),
            "created_at": self.created_at.isoformat() if self.created_at else "",
        }


@dataclass
class ScreenerResult:
    """스크리너 결과"""
    date: date
    total_candidates: int
    filtered_count: int
    signals: List[Signal]
    by_grade: Dict[str, int] = field(default_factory=dict)
    by_market: Dict[str, int] = field(default_factory=dict)
    processing_time_ms: float = 0
    
    def to_dict(self) -> Dict:
        return {
            "date": self.date.isoformat(),
            "total_candidates": self.total_candidates,
            "filtered_count": self.filtered_count,
            "signals": [s.to_dict() for s in self.signals],
            "by_grade": self.by_grade,
            "by_market": self.by_market,
            "processing_time_ms": self.processing_time_ms,
        }


@dataclass
class Position:
    """포지션 정보"""
    entry_price: float
    stop_price: float
    target_price: float
    r_value: float
    position_size: float
    quantity: int
    r_multiplier: float
