"""대출 데이터 저장소 (Repository 패턴)"""

from typing import List, Optional
from src.models.loan import Loan
from src.services.drive_storage import save_json, load_json
from src.utils.helpers import now_iso


LOANS_FILE = "loans.json"


def get_all_loans() -> List[Loan]:
    """모든 대출 목록 조회"""
    data = load_json(LOANS_FILE, default=[])
    return [Loan.from_dict(item) for item in data]


def get_active_loans() -> List[Loan]:
    """진행중 대출만 조회 (이자율 높은 순)"""
    loans = get_all_loans()
    active = [loan for loan in loans if loan.status == "진행중"]
    active.sort(key=lambda x: x.get_priority_score(), reverse=True)
    return active


def get_loan_by_id(loan_id: str) -> Optional[Loan]:
    """ID로 대출 조회"""
    for loan in get_all_loans():
        if loan.loan_id == loan_id:
            return loan
    return None


def save_loan(loan: Loan) -> Loan:
    """대출 저장 (신규 또는 업데이트)"""
    loans = get_all_loans()
    
    found_index = -1
    for i, existing in enumerate(loans):
        if existing.loan_id == loan.loan_id:
            found_index = i
            break
    
    loan.updated_at = now_iso()
    if found_index >= 0:
        loans[found_index] = loan
    else:
        loans.append(loan)
    
    data = [l.to_dict() for l in loans]
    save_json(data, LOANS_FILE)
    
    return loan


def delete_loan(loan_id: str) -> bool:
    """대출 삭제"""
    loans = get_all_loans()
    original_count = len(loans)
    loans = [l for l in loans if l.loan_id != loan_id]
    
    if len(loans) == original_count:
        return False
    
    data = [l.to_dict() for l in loans]
    save_json(data, LOANS_FILE)
    return True


def initialize_default_loans():
    """초기 3건 대출 등록"""
    print("=" * 60)
    print("📋 초기 대출 데이터 등록")
    print("=" * 60)
    
    existing = get_all_loans()
    if existing:
        print(f"\n⚠️  이미 {len(existing)}건의 대출이 등록되어 있습니다.")
        for loan in existing:
            print(f"   • {loan.loan_name}: {loan.current_balance:,.0f}원")
        return existing
    
    loan1 = Loan(
        loan_name="신용대출2 - 신세대플러스론",
        bank_name="우리은행",
        account_number="1200-904-840811",
        loan_type="신용대출",
        repayment_method="만기일시",
        initial_amount=75000000,
        current_balance=60037000,
        start_date="2020-06-10",
        maturity_date="2026-06-12",
        payment_day=10,
        interest_rate=5.58,
        rate_type="변동",
        rate_base="KORIBOR",
        rate_spread=2.78,
        branch="오리역지점",
        status="진행중",
        memo="만기 임박 - 연장 검토 필요"
    )
    
    loan2 = Loan(
        loan_name="신용대출1 - 우리 WON하는 직장인 대출",
        bank_name="우리은행",
        account_number="1200-106-006649",
        loan_type="신용대출",
        repayment_method="만기일시",
        initial_amount=30000000,
        current_balance=28250100,
        start_date="2024-02-26",
        maturity_date="2027-02-26",
        payment_day=26,
        interest_rate=4.67,
        rate_type="고정",
        rate_base="고정금리",
        rate_spread=1.75,
        branch="대치역금융센터",
        status="진행중"
    )
    
    loan3 = Loan(
        loan_name="주택자금대출 - 우리아파트론",
        bank_name="우리은행",
        account_number="1203-101-904146",
        loan_type="주택자금대출",
        repayment_method="원리금균등",
        initial_amount=350000000,
        current_balance=291277581,
        start_date="2020-11-10",
        maturity_date="2045-10-10",
        payment_day=10,
        interest_rate=3.83,
        rate_type="변동",
        rate_base="신잔액기준 COFIX",
        rate_spread=1.34,
        branch="서현동지점",
        status="진행중",
        memo="구입자금보증(MCG)"
    )
    
    print("\n📝 대출 등록 중...")
    save_loan(loan1)
    save_loan(loan2)
    save_loan(loan3)
    
    print("\n📋 등록된 대출 (이자율 높은 순):")
    for i, loan in enumerate(get_active_loans(), 1):
        print(f"   {i}. {loan.loan_name}")
        print(f"      잔액: {loan.current_balance:,.0f}원, 금리: {loan.interest_rate}%")
    
    total = sum(l.current_balance for l in get_active_loans())
    print(f"\n💰 총 잔액: {total:,.0f}원")
    
    print("\n" + "=" * 60)
    print("✅ 초기 데이터 등록 완료!")
    print("=" * 60)
    
    return get_active_loans()


if __name__ == '__main__':
    initialize_default_loans()
