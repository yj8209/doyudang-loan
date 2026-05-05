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
def add_regular_payment(
    loan_id: str,
    payment_date: str,
    principal_amount: float = 0,
    interest_amount: float = 0,
    overdue_interest: float = 0,
    memo: str = "",
    created_by: str = ""
) -> dict:
    """
    정기상환 처리 (매월 자동 차감)
    
    - 만기일시 대출: 이자만 입력 (원금 0)
    - 원리금균등 대출: 원금 + 이자 분리 입력
    - 잔액에서 원금만 차감 (이자는 비용일 뿐, 잔액에 영향 없음)
    """
    loan = get_loan_by_id(loan_id)
    if not loan:
        return {
            'success': False,
            'message': f'❌ 대출을 찾을 수 없습니다: {loan_id}',
            'payment': None,
            'loan': None,
        }
    
    # 검증
    if principal_amount < 0 or interest_amount < 0:
        return {
            'success': False,
            'message': '❌ 금액은 0 이상이어야 합니다.',
            'payment': None,
            'loan': None,
        }
    
    total = principal_amount + interest_amount + overdue_interest
    if total == 0:
        return {
            'success': False,
            'message': '❌ 원금 또는 이자 중 하나는 입력해야 합니다.',
            'payment': None,
            'loan': None,
        }
    
    # 원금이 잔액보다 크면 안 됨
    if principal_amount > loan.current_balance:
        return {
            'success': False,
            'message': (
                f'❌ 원금({principal_amount:,.0f}원)이 잔액'
                f'({loan.current_balance:,.0f}원)보다 큽니다.'
            ),
            'payment': None,
            'loan': None,
        }
    
    # 상환 후 잔액 (원금만 차감)
    new_balance = loan.current_balance - principal_amount
    
    # Payment 객체 생성
    payment = Payment(
        loan_id=loan_id,
        payment_date=payment_date,
        payment_type="정기상환",
        principal_amount=principal_amount,
        interest_amount=interest_amount,
        overdue_interest=overdue_interest,
        total_amount=total,
        balance_after=new_balance,
        memo=memo,
        status="확정",
        created_by=created_by
    )
    
    # 1. 상환 저장
    save_payment(payment)
    
    # 2. 대출 잔액 갱신 (원금만 차감)
    loan.update_balance(new_balance)
    
    # 3. 완납 여부 확인
    if new_balance == 0:
        loan.status = "완납"
        loan.memo = (loan.memo or "") + f"\n[자동] {payment_date}에 완납 처리됨"
    
    save_loan(loan)
    
    return {
        'success': True,
        'message': (
            f'✅ {loan.loan_name} 정기상환 확정\n'
            f'   원금: {principal_amount:,.0f}원, 이자: {interest_amount:,.0f}원\n'
            f'   잔액: {loan.current_balance + principal_amount:,.0f}원 → {new_balance:,.0f}원'
        ),
        'payment': payment,
        'loan': loan,
    }


def get_recent_regular_payments(loan_id: str, limit: int = 3) -> List[Payment]:
    """최근 정기상환 N건 조회"""
    payments = get_payments_by_loan(loan_id)
    regular_only = [p for p in payments if p.payment_type == "정기상환"]
    return regular_only[:limit]


def estimate_monthly_interest(loan) -> float:
    """대출의 월 이자 추정 (잔액 × 금리 / 12)"""
    monthly_rate = loan.interest_rate / 100 / 12
    return loan.current_balance * monthly_rate


def estimate_monthly_payment(loan) -> dict:
    """
    매월 정기상환 예상액 계산
    
    Returns:
        {
            'expected_principal': 예상 원금,
            'expected_interest': 예상 이자,
            'expected_total': 예상 총액
        }
    """
    expected_interest = estimate_monthly_interest(loan)
    
    if loan.repayment_method == "만기일시":
        # 만기일시: 이자만 매월
        return {
            'expected_principal': 0,
            'expected_interest': expected_interest,
            'expected_total': expected_interest,
        }
    elif loan.repayment_method == "원리금균등":
        # 원리금균등: 매월 원금 + 이자 (간단 추정)
        # 실제 계산은 PMT 공식이지만, 사용자가 거래내역 보고 입력하므로 추정만 제공
        try:
            from datetime import datetime
            maturity = datetime.strptime(loan.maturity_date, "%Y-%m-%d")
            today = datetime.now()
            months_left = max(1, (maturity.year - today.year) * 12 + (maturity.month - today.month))
            
            # 단순 추정: 잔액 / 남은 개월 + 이자
            expected_principal = loan.current_balance / months_left
            return {
                'expected_principal': expected_principal,
                'expected_interest': expected_interest,
                'expected_total': expected_principal + expected_interest,
            }
        except:
            return {
                'expected_principal': 0,
                'expected_interest': expected_interest,
                'expected_total': expected_interest,
            }
    else:
        return {
            'expected_principal': 0,
            'expected_interest': expected_interest,
            'expected_total': expected_interest,
        }