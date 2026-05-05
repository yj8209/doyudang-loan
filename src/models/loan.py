"""대출 데이터 모델"""

from dataclasses import dataclass, field, asdict
from typing import List
from src.utils.helpers import generate_id, now_iso


LOAN_TYPES = ["신용대출", "주택자금대출", "사업자대출", "기타"]
REPAYMENT_METHODS = ["만기일시", "원리금균등", "원금균등"]
RATE_TYPES = ["고정", "변동"]
LOAN_STATUSES = ["진행중", "완납", "연장됨"]


@dataclass
class LoanChangeLog:
    """대출 변경 이력"""
    change_date: str          # 변경 날짜
    change_type: str          # "신규등록" / "만기연장" / "금리변경" / "잔액수정" / "메모수정" 등
    
    # 변경 전/후 값
    field_changed: str = ""   # 변경된 필드명
    old_value: str = ""
    new_value: str = ""
    
    # 추가 정보
    reason: str = ""          # 변경 사유
    memo: str = ""            # 자유 메모
    changed_by: str = ""      # 변경자
    
    # 시스템 필드
    log_id: str = field(default_factory=generate_id)
    created_at: str = field(default_factory=now_iso)
    
    def to_dict(self):
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data):
        return cls(**data)


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
    
    # 변경 이력
    change_logs: List[dict] = field(default_factory=list)
    
    # 시스템 필드
    loan_id: str = field(default_factory=generate_id)
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)
    
    def to_dict(self):
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data):
        # change_logs 호환성
        if 'change_logs' not in data:
            data['change_logs'] = []
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
    
    def add_change_log(
        self,
        change_type: str,
        field_changed: str = "",
        old_value: str = "",
        new_value: str = "",
        reason: str = "",
        memo: str = "",
        changed_by: str = ""
    ):
        """변경 이력 추가"""
        log = LoanChangeLog(
            change_date=now_iso()[:10],  # YYYY-MM-DD
            change_type=change_type,
            field_changed=field_changed,
            old_value=str(old_value),
            new_value=str(new_value),
            reason=reason,
            memo=memo,
            changed_by=changed_by
        )
        self.change_logs.append(log.to_dict())
        self.updated_at = now_iso()
    
    def get_recent_changes(self, limit=5):
        """최근 변경 이력 N건"""
        return self.change_logs[-limit:][::-1]  # 최신순 반전
    
    def extend_maturity(
        self,
        new_maturity_date: str,
        new_interest_rate: float = None,
        new_rate_type: str = None,
        new_rate_spread: float = None,
        reason: str = "만기 연장",
        changed_by: str = ""
    ):
        """만기 연장 (만기일 + 금리 변경 가능)"""
        old_maturity = self.maturity_date
        
        # 만기일 변경
        self.maturity_date = new_maturity_date
        self.add_change_log(
            change_type="만기연장",
            field_changed="maturity_date",
            old_value=old_maturity,
            new_value=new_maturity_date,
            reason=reason,
            changed_by=changed_by
        )
        
        # 금리 변경 (선택)
        if new_interest_rate is not None and new_interest_rate != self.interest_rate:
            old_rate = self.interest_rate
            self.interest_rate = new_interest_rate
            self.add_change_log(
                change_type="금리변경",
                field_changed="interest_rate",
                old_value=f"{old_rate}%",
                new_value=f"{new_interest_rate}%",
                reason=f"만기 연장 시 금리 변경",
                changed_by=changed_by
            )
        
        # 변동/고정 변경 (선택)
        if new_rate_type is not None and new_rate_type != self.rate_type:
            old_type = self.rate_type
            self.rate_type = new_rate_type
            self.add_change_log(
                change_type="금리종류변경",
                field_changed="rate_type",
                old_value=old_type,
                new_value=new_rate_type,
                reason=f"만기 연장 시 금리 종류 변경",
                changed_by=changed_by
            )
        
        # 가산금리 변경 (선택)
        if new_rate_spread is not None and new_rate_spread != self.rate_spread:
            old_spread = self.rate_spread
            self.rate_spread = new_rate_spread
            self.add_change_log(
                change_type="가산금리변경",
                field_changed="rate_spread",
                old_value=f"{old_spread}%",
                new_value=f"{new_rate_spread}%",
                reason=f"만기 연장 시 가산금리 변경",
                changed_by=changed_by
            )
        
        # 메모에 연장 기록
        self.memo = (self.memo or "") + f"\n[{now_iso()[:10]}] 만기 연장: {old_maturity} → {new_maturity_date}"