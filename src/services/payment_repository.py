"""
상환 데이터 저장소
- 상환 이력의 CRUD
- 부분 상환 시 대출 잔액 자동 갱신
"""

from typing import List, Optional
from src.models.payment import Payment
from src.models.loan import Loan
from src.services.drive_storage import save_json, load_json
from src.services.loan_repository import save_loan, get_loan_by_id
from src.utils.helpers import now_iso


PAYMENTS_FILE = "payments.json"


def get_all_payments() -> List[Payment]:
    """모든 상환 이력 조회"""
    data = load_json(PAYMENTS_FILE, default=[])
    return [Payment.from_dict(item) for item in data]


def get_payments_by_loan(loan_id: str) -> List[Payment]:
    """특정 대출의 상환 이력만 조회 (최신순)"""
    payments = get_all_payments()
    filtered = [p for p in payments if p.loan_id == loan_id and p.is_active()]
    filtered.sort(key=lambda x: x.payment_date, reverse=True)
    return filtered


def save_payment(payment: Payment) -> Payment:
    """상환 저장"""
    payments = get_all_payments()
    
    # 기존 상환 찾기
    found_index = -1
    for i, existing in enumerate(payments):
        if existing.payment_id == payment.payment_id:
            found_index = i
            break
    
    # 업데이트 또는 추가
    if found_index >= 0:
        payments[found_index] = payment
    else:
        payments.append(payment)
    
    # Drive에 저장
    data = [p.to_dict() for p in payments]
    save_json(data, PAYMENTS_FILE)
    
    return payment


def add_partial_payment(
    loan_id: str,
    amount: float,
    payment_date: str,
    source: str = "",
    source_detail: str = "",
    memo: str = "",
    created_by: str = ""
) -> dict:
    """
    부분 상환 추가
    1. 대출 잔액 자동 차감
    2. 상환 이력 기록
    
    Returns:
        {
            'success': bool,
            'message': str,
            'payment': Payment or None,
            'loan': Loan or None,
        }
    """
    # 대출 조회
    loan = get_loan_by_id(loan_id)
    if not loan:
        return {
            'success': False,
            'message': f'❌ 대출을 찾을 수 없습니다: {loan_id}',
            'payment': None,
            'loan': None,
        }
    
    # 상환 금액 검증
    if amount <= 0:
        return {
            'success': False,
            'message': '❌ 상환 금액은 0보다 커야 합니다.',
            'payment': None,
            'loan': None,
        }
    
    if amount > loan.current_balance:
        return {
            'success': False,
            'message': (
                f'❌ 상환 금액({amount:,.0f}원)이 잔액'
                f'({loan.current_balance:,.0f}원)보다 큽니다.'
            ),
            'payment': None,
            'loan': None,
        }
    
    # 상환 후 잔액 계산
    new_balance = loan.current_balance - amount
    
    # Payment 객체 생성
    payment = Payment(
        loan_id=loan_id,
        payment_date=payment_date,
        payment_type="부분상환",
        principal_amount=amount,
        interest_amount=0,
        total_amount=amount,
        balance_after=new_balance,
        source=source,
        source_detail=source_detail,
        memo=memo,
        status="확정",
        created_by=created_by
    )
    
    # 1. 상환 저장
    save_payment(payment)
    
    # 2. 대출 잔액 갱신
    loan.update_balance(new_balance)
    
    # 3. 완납 여부 확인
    if new_balance == 0:
        loan.status = "완납"
        loan.memo = (loan.memo or "") + f"\n[자동] {payment_date}에 완납 처리됨"
    
    save_loan(loan)
    
    return {
        'success': True,
        'message': (
            f'✅ {loan.loan_name}에 {amount:,.0f}원 부분 상환 완료\n'
            f'   잔액: {loan.current_balance + amount:,.0f}원 → {new_balance:,.0f}원'
        ),
        'payment': payment,
        'loan': loan,
    }


def get_total_repaid(loan_id: str) -> float:
    """특정 대출의 누적 상환 원금"""
    payments = get_payments_by_loan(loan_id)
    return sum(p.principal_amount for p in payments)


def get_total_interest_paid(loan_id: str) -> float:
    """특정 대출의 누적 납부 이자"""
    payments = get_payments_by_loan(loan_id)
    return sum(p.interest_amount + p.overdue_interest for p in payments)