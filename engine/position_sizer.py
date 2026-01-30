"""
자금 관리 - R값 기반 포지션 사이징
"""

from engine.config import SignalConfig, Grade
from engine.models import Position


class PositionSizer:
    """R값 기반 포지션 사이저"""
    
    def __init__(self, capital: float, config: SignalConfig = None):
        """
        Args:
            capital: 총 자본금
            config: 시그널 설정
        """
        self.capital = capital
        self.config = config or SignalConfig()
        
        # R값 = 자본금 * R비율 (기본 0.5%)
        self.r_value = capital * self.config.r_ratio
    
    def calculate(self, entry_price: float, grade: Grade) -> Position:
        """
        포지션 계산
        
        Args:
            entry_price: 진입가
            grade: 등급
            
        Returns:
            Position 객체
        """
        # 등급별 R 배수
        grade_config = self.config.grade_configs.get(grade)
        r_multiplier = grade_config.r_multiplier if grade_config else 1.0
        
        # C등급은 매매 안함
        if grade == Grade.C or r_multiplier == 0:
            return Position(
                entry_price=entry_price,
                stop_price=entry_price * (1 - self.config.stop_loss_pct),
                target_price=entry_price * (1 + self.config.take_profit_pct),
                r_value=0,
                position_size=0,
                quantity=0,
                r_multiplier=0
            )
        
        # 손절가 계산 (-3%)
        stop_price = entry_price * (1 - self.config.stop_loss_pct)
        
        # 목표가 계산 (+5%)
        target_price = entry_price * (1 + self.config.take_profit_pct)
        
        # 리스크 계산 (진입가 - 손절가)
        risk_per_share = entry_price - stop_price
        
        if risk_per_share <= 0:
            risk_per_share = entry_price * self.config.stop_loss_pct
        
        # 실제 리스크 금액 = R값 * R배수
        actual_risk = self.r_value * r_multiplier
        
        # 수량 계산 = 리스크 금액 / 주당 리스크
        quantity = int(actual_risk / risk_per_share) if risk_per_share > 0 else 0
        
        # 최소 1주
        quantity = max(1, quantity)
        
        # 포지션 사이즈 = 수량 * 진입가
        position_size = quantity * entry_price
        
        # 최대 포지션 한도 체크 (자본의 20%)
        max_position = self.capital * 0.2
        if position_size > max_position:
            quantity = int(max_position / entry_price)
            position_size = quantity * entry_price
        
        return Position(
            entry_price=entry_price,
            stop_price=stop_price,
            target_price=target_price,
            r_value=risk_per_share * quantity,
            position_size=position_size,
            quantity=quantity,
            r_multiplier=r_multiplier
        )
    
    def get_summary(self) -> dict:
        """자금 관리 요약"""
        return {
            "capital": self.capital,
            "r_value": self.r_value,
            "r_ratio_pct": self.config.r_ratio * 100,
            "stop_loss_pct": self.config.stop_loss_pct * 100,
            "take_profit_pct": self.config.take_profit_pct * 100,
            "max_positions": self.config.max_positions,
        }
