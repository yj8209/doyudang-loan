"""이벤트 자금 데이터 모델"""

from dataclasses import dataclass, field, asdict
from src.utils.helpers import generate_id, now_iso


# 이벤트 종류
EVENT_TYPES = [
    "남편 보너스",
    "대표 수입",
    "적금 만기",
    "예금 만기",
    "주식 매도",
    "주식 배당",
    "투자 수익",
    "기타 수입",
    "지출 예정",
]

# 사용 우선순위
USE_PRIORITY = [
    "부분상환",      # 부분상환 우선
    "비상금",        # 비상금으로 보유
    "투자",          # 다른 투자
    "지출",          # 지출 예정
    "미정",          # 아직 결정 안 함
]


@dataclass
class FundEvent:
    """이벤트 자금 정보"""
    
    event_name: str            # 이벤트 이름 (예: "5월 보너스", "11월 적금 만기")
    event_type: str            # 이벤트 종류 (남편 보너스, 적금 만기 등)
    amount: float              # 금액
    
    # 일정
    expected_date: str         # 예상 날짜 (YYYY-MM-DD)
    
    # 상태
    is_received: bool = False  # 수령/실현 여부
    actual_date: str = ""      # 실제 수령일
    actual_amount: float = 0   # 실제 수령액 (예상과 다를 수 있음)
    
    # 사용 계획
    use_priority: str = "미정"  # 사용 우선순위
    target_loan_id: str = ""    # 부분상환 시 대상 대출
    used_amount: float = 0      # 실제 사용한 금액
    
    # 메타
    memo: str = ""
    created_by: str = ""
    
    # 시스템 필드
    event_id: str = field(default_factory=generate_id)
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)
    
    def to_dict(self):
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data):
        return cls(**data)
    
    def get_status(self) -> str:
        """상태 표시"""
        from datetime import datetime, date
        
        if self.is_received:
            return "✅ 수령 완료"
        
        try:
            expected = datetime.strptime(self.expected_date, "%Y-%m-%d").date()
            today = date.today()
            
            if expected < today:
                return "⚠️ 지연됨"
            elif (expected - today).days <= 30:
                return f"🔵 곧 수령 ({(expected - today).days}일 후)"
            else:
                return "📅 예정"
        except:
            return "❓ 미정"
    
    def get_remaining_amount(self) -> float:
        """남은 금액 (수령액 - 사용액)"""
        if self.is_received:
            return self.actual_amount - self.used_amount
        return self.amount