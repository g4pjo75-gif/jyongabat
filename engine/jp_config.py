"""
일본 시장(JPX) 시그널 생성기 설정
JPX Nikkei 400 기반
"""

from dataclasses import dataclass, field
from typing import Dict, List
from enum import Enum


class Grade(Enum):
    """종목 등급"""
    S = "S"  # 최고 - 풀배팅
    A = "A"  # 우수 - 기본배팅
    B = "B"  # 보통 - 절반배팅
    C = "C"  # 미달 - 매매안함


@dataclass
class GradeConfig:
    """등급별 설정"""
    min_trading_value: int      # 최소 거래대금 (엔)
    min_change_pct: float       # 최소 등락률 (%)
    max_change_pct: float       # 최대 등락률 (%)
    min_score: int              # 최소 점수
    r_multiplier: float         # R 배수


@dataclass
class JPSignalConfig:
    """일본 시장 시그널 설정 (엔화 기준)"""
    
    # === 기본 필터 === (일본 시장 기준 - 엔화)
    # 한국: 30억원 = 약 3억엔 (환율 약 10:1 기준)
    min_trading_value: int = 300_000_000        # 최소 거래대금: 3억엔
    min_change_pct: float = -2.0                # 최소 등락률: -2.0% (보합/약세 종목도 포함하여 분석 대상 확대)
    max_change_pct: float = 29.9                # 최대 등락률: 29.9% (스트레이트 상한가 제외)
    min_price: int = 100                        # 최소 주가: 100엔
    max_price: int = 100000                     # 최대 주가: 10만엔
    
    # === 제외 조건 ===
    exclude_etf: bool = True
    exclude_etn: bool = True
    exclude_reit: bool = True
    exclude_keywords: List[str] = field(default_factory=lambda: [
        "ETF", "ETN", "REIT", "投資法人", "インバース", "レバレッジ",
        "ブル", "ベア", "ダブル", "トリプル",
    ])
    
    # === 점수 가중치 (12점 만점) ===
    score_weights: Dict[str, int] = field(default_factory=lambda: {
        "news": 3,           # 뉴스/재료 (필수)
        "volume": 3,         # 거래대금 (필수)
        "chart": 2,          # 차트패턴
        "candle": 1,         # 캔들형태
        "consolidation": 1,  # 기간조정
        "supply": 2,         # 수급
    })
    
    # === 등급별 기준 === (엔화 기준)
    grade_configs: Dict[Grade, GradeConfig] = field(default_factory=lambda: {
        Grade.S: GradeConfig(
            min_trading_value=5_000_000_000,    # 50억엔
            min_change_pct=5.0,
            max_change_pct=20.0,
            min_score=9,
            r_multiplier=1.5,
        ),
        Grade.A: GradeConfig(
            min_trading_value=2_000_000_000,    # 20억엔
            min_change_pct=3.0,
            max_change_pct=15.0,
            min_score=7,
            r_multiplier=1.0,
        ),
        Grade.B: GradeConfig(
            min_trading_value=500_000_000,      # 5억엔
            min_change_pct=1.0,
            max_change_pct=12.0,
            min_score=5,
            r_multiplier=0.5,
        ),
        Grade.C: GradeConfig(
            min_trading_value=300_000_000,      # 3억엔
            min_change_pct=0.5,
            max_change_pct=29.9,
            min_score=0,
            r_multiplier=0.0,
        ),
    })
    
    # === 매매 설정 ===
    stop_loss_pct: float = 0.03       # 손절: -3%
    take_profit_pct: float = 0.05     # 익절: +5%
    gap_target_pct: float = 0.03      # 갭상승 익절: +3%
    gap_stop_pct: float = -0.02       # 갭하락 손절: -2%
    time_stop_hour: int = 10          # 시간손절: 10시
    
    # === 리스크 관리 ===
    r_ratio: float = 0.005            # R 비율: 0.5%
    max_positions: int = 30           # 최대 동시 보유
    daily_loss_limit_r: float = 2.0   # 일일 손실 한도: 2R
    weekly_loss_limit_r: float = 4.0  # 주간 손실 한도: 4R
    
    # === 일본어 뉴스 키워드 ===
    positive_keywords: List[str] = field(default_factory=lambda: [
        # 실적 관련 (業績関連)
        "黒字転換", "増益", "最高益", "好決算", "上方修正",
        "売上増", "営業利益", "純利益", "過去最高",
        # 계약/수주 (契約・受注)
        "受注", "契約締結", "供給契約", "大型契約", "提携",
        "MOU", "業務提携", "資本提携",
        # 신사업/기술 (新規事業・技術)
        "新薬", "承認", "FDA", "特許取得", "技術移転",
        "ライセンス", "新製品", "量産", "商用化",
        # 투자/M&A (投資・M&A)
        "出資", "買収", "子会社化", "株式取得",
        # 정책/테마 (政策・テーマ)
        "政府支援", "国策", "関連銘柄", "テーマ株",
        # 수급 (需給)
        "外国人買い", "機関投資家", "自社株買い",
        # 일반 긍정
        "急騰", "ストップ高", "年初来高値", "高値更新",
    ])
    
    negative_keywords: List[str] = field(default_factory=lambda: [
        # 부정적 이슈 (ネガティブ)
        "不正", "粉飾", "上場廃止", "監理銘柄", "債務超過",
        "破産", "民事再生", "検察", "逮捕", "起訴",
        # 실적 악화 (業績悪化)
        "赤字転落", "赤字拡大", "業績悪化", "減収減益",
        "下方修正",
        # 수급 악화 (需給悪化)
        "大量売り", "空売り増加", "外国人売り",
        # 일반 부정
        "急落", "ストップ安", "年初来安値",
    ])
    
    @classmethod
    def default(cls):
        return cls()
