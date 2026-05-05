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
def get_all_payments() -> List[Payment]:
    """모든 상환 이력 조회 (날짜 최신순)"""
    payments = load_json(PAYMENTS_FILE) or []
    
    payment_list = []
    for data in payments:
        try:
            p = Payment.from_dict(data)
            payment_list.append(p)
        except Exception as e:
            print(f"⚠️ payment 로드 실패: {e}")
    
    # 날짜 최신순으로 정렬
    payment_list.sort(key=lambda p: p.payment_date, reverse=True)
    
    return payment_list


def get_payment_by_id(payment_id: str) -> Payment:
    """특정 상환 이력 조회"""
    all_payments = get_all_payments()
    for p in all_payments:
        if p.payment_id == payment_id:
            return p
    return None


def update_payment(
    payment_id: str,
    new_principal: float = None,
    new_interest: float = None,
    new_overdue: float = None,
    new_date: str = None,
    new_source: str = None,
    new_memo: str = None,
    changed_by: str = ""
) -> dict:
    """
    기존 상환 이력 수정 + 잔액 자동 보정
    
    주의: 잔액 변경에 영향을 주므로 신중하게!
    """
    # 1. 기존 payment 가져오기
    payment = get_payment_by_id(payment_id)
    if not payment:
        return {
            'success': False,
            'message': f'❌ 상환 이력을 찾을 수 없습니다.',
            'payment': None,
        }
    
    # 2. 대출 가져오기
    loan = get_loan_by_id(payment.loan_id)
    if not loan:
        return {
            'success': False,
            'message': f'❌ 대출을 찾을 수 없습니다.',
            'payment': None,
        }
    
    # 3. 변경 전 원금 (잔액 보정용)
    old_principal = payment.principal_amount
    
    # 4. 새 값 적용
    if new_principal is not None:
        payment.principal_amount = float(new_principal)
    if new_interest is not None:
        payment.interest_amount = float(new_interest)
    if new_overdue is not None:
        payment.overdue_interest = float(new_overdue)
    if new_date is not None:
        payment.payment_date = new_date
    if new_source is not None:
        payment.source = new_source
    if new_memo is not None:
        payment.memo = new_memo
    
    # 5. 총액 재계산
    payment.total_amount = (
        payment.principal_amount + 
        payment.interest_amount + 
        payment.overdue_interest
    )
    
    # 6. 잔액 보정 (원금 변경 시)
    new_principal_value = payment.principal_amount
    principal_diff = new_principal_value - old_principal
    
    if principal_diff != 0:
        # 대출 잔액에서 차이만큼 더 빼거나 (원금 증가) 더하거나 (원금 감소)
        loan.current_balance = loan.current_balance - principal_diff
        loan.update_balance(loan.current_balance)
        save_loan(loan)
    
    # 7. balance_after 갱신
    payment.balance_after = loan.current_balance
    
    # 8. 변경 이력 메모 추가
    payment.memo = (payment.memo or "") + f"\n[{now_iso()[:10]}] 수정됨 ({changed_by})"
    
    # 9. payment 저장 (전체 다시 저장)
    all_payments = get_all_payments()
    
    # 기존 payment 교체
    for i, p in enumerate(all_payments):
        if p.payment_id == payment_id:
            all_payments[i] = payment
            break
    
    # 전체 다시 저장
    payments_data = [p.to_dict() for p in all_payments]
    save_json(PAYMENTS_FILE, payments_data)
    
    return {
        'success': True,
        'message': (
            f'✅ 상환 이력 수정 완료\n'
            f'   원금: {old_principal:,.0f}원 → {new_principal_value:,.0f}원\n'
            f'   잔액 보정: {principal_diff:+,.0f}원'
        ),
        'payment': payment,
    }


def delete_payment(
    payment_id: str,
    reason: str = "",
    changed_by: str = ""
) -> dict:
    """
    상환 이력 삭제 + 잔액 자동 복원
    
    주의: 잔액에서 차감했던 원금을 복원합니다!
    """
    # 1. 삭제할 payment 가져오기
    payment = get_payment_by_id(payment_id)
    if not payment:
        return {
            'success': False,
            'message': f'❌ 상환 이력을 찾을 수 없습니다.',
        }
    
    # 2. 대출 가져오기
    loan = get_loan_by_id(payment.loan_id)
    if not loan:
        return {
            'success': False,
            'message': f'❌ 대출을 찾을 수 없습니다.',
        }
    
    # 3. 잔액 복원 (차감했던 원금만큼 다시 더하기)
    old_balance = loan.current_balance
    new_balance = old_balance + payment.principal_amount
    
    # 최초 금액보다 많아질 수 없음
    if new_balance > loan.initial_amount:
        return {
            'success': False,
            'message': (
                f'❌ 잔액 복원 시 최초 금액({loan.initial_amount:,.0f}원)을 '
                f'초과합니다. 데이터 정합성 오류 가능성 있음.'
            ),
        }
    
    loan.update_balance(new_balance)
    
    # 4. 완납 상태였으면 진행중으로 복원
    if loan.status == "완납":
        loan.status = "진행중"
        loan.memo = (loan.memo or "") + f"\n[{now_iso()[:10]}] 상환 삭제로 진행중 복원"
    
    save_loan(loan)
    
    # 5. payment 삭제
    all_payments = get_all_payments()
    all_payments = [p for p in all_payments if p.payment_id != payment_id]
    
    payments_data = [p.to_dict() for p in all_payments]
    save_json(PAYMENTS_FILE, payments_data)
    
    return {
        'success': True,
        'message': (
            f'✅ 상환 이력 삭제 완료\n'
            f'   삭제된 금액: {payment.principal_amount:,.0f}원\n'
            f'   잔액 복원: {old_balance:,.0f}원 → {new_balance:,.0f}원'
        ),
    }


def get_payments_with_filters(
    loan_id: str = None,
    payment_type: str = None,
    days_back: int = None
) -> List[Payment]:
    """필터링된 상환 이력 조회"""
    from datetime import datetime, timedelta
    
    all_payments = get_all_payments()
    
    # 대출 필터
    if loan_id:
        all_payments = [p for p in all_payments if p.loan_id == loan_id]
    
    # 종류 필터
    if payment_type:
        all_payments = [p for p in all_payments if p.payment_type == payment_type]
    
    # 기간 필터
    if days_back:
        cutoff = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        all_payments = [p for p in all_payments if p.payment_date >= cutoff]
    
    return all_payments    