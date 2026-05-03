"""대출 데이터 모델"""

from dataclasses import dataclass, field, asdict
from src.utils.helpers import generate_id, now_iso


LOAN_TYPES = ["신용대출", "주택자금대출", "기타"]
REPAYMENT_METHODS = ["만기일시", "원리금균등", "원금균등"]
RATE_TYPES = ["고정", "변동"]
LOAN_STATUSES = ["진행중", "완납", "연장됨"]


@dataclass
class Loan:
    """대출 정보"""
    
    loan_name: str
    bank_name: str
    account_number: str
    loan_type: str
    repayment_method: str
    initial_amount: float
    current_balance: float
    start_date: str
    maturity_date: str
    payment_day: int
    interest_rate: float
    rate_type: str
    rate_base: str = ""
    rate_spread: float = 0.0
    branch: str = ""
    status: str = "진행중"
    memo: str = ""
    loan_id: str = field(default_factory=generate_id)
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)
    
    def to_dict(self):
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data):
        return cls(**data)
    
    def update_balance(self, new_balance):
        self.current_balance = new_balance
        self.updated_at = now_iso()
    
    def get_priority_score(self):
        if self.status != "진행중":
            return -1
        return self.interest_rate
    
    def get_progress_percent(self):
        if self.initial_amount == 0:
            return 0
        repaid = self.initial_amount - self.current_balance
        return (repaid / self.initial_amount) * 100
