"""
상환 데이터 모델
- 부분 상환 (수시)
- 정기 상환 (매월 자동 차감)
- 이자 납부 (만기일시 대출)
"""

from dataclasses import dataclass, field, asdict
from src.utils.helpers import generate_id, now_iso


# 상환 종류
PAYMENT_TYPES = [
    "부분상환",      # 수시 추가 상환
    "정기상환",      # 원리금균등 매월 자동
    "이자납부",      # 만기일시 매월 이자만
    "만기상환",      # 만기일시 만기에 일시 상환
    "일부상환",      # 만기 연장 시 일부만 상환
]

# 자금 출처 (부분 상환에 주로 사용)
PAYMENT_SOURCES = [
    "월급 잉여",
    "남편 보너스",
    "추가 상여금",
    "적금 만기",
    "회사 주식",
    "보유 주식",
    "기타",
]

# 상환 상태
PAYMENT_STATUSES = ["확정", "예상", "취소"]


@dataclass
class Payment:
    """상환 정보"""
    
    # 필수 정보
    loan_id: str                       # 어느 대출의 상환인지
    payment_date: str                  # 상환일 (YYYY-MM-DD)
    payment_type: str                  # 부분상환/정기상환/이자납부 등
    
    # 금액 정보 (3가지 중 해당하는 것만 입력)
    principal_amount: float = 0        # 원금 (부분상환, 정기상환의 원금)
    interest_amount: float = 0         # 이자 (정기상환의 이자, 이자납부)
    overdue_interest: float = 0        # 연체이자 (보통 0)
    
    # 자동 계산
    total_amount: float = 0            # 총액 = 원금 + 이자 + 연체이자
    balance_after: float = 0           # 상환 후 잔액
    
    # 추가 정보
    source: str = ""                   # 자금 출처 (부분상환만)
    source_detail: str = ""            # 출처 상세 메모
    memo: str = ""                     # 자유 메모
    status: str = "확정"                # 확정/예상/취소
    
    # 시스템 필드
    payment_id: str = field(default_factory=generate_id)
    created_by: str = ""               # 입력자 (대표님 / 남편)
    created_at: str = field(default_factory=now_iso)
    
    def __post_init__(self):
        """초기화 후 자동 계산"""
        if self.total_amount == 0:
            self.total_amount = (
                self.principal_amount + 
                self.interest_amount + 
                self.overdue_interest
            )
    
    def to_dict(self):
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data):
        return cls(**data)
    
    def is_active(self):
        """확정된 상환인지"""
        return self.status == "확정"