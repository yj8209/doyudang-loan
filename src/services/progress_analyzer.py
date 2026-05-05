"""
5년 진행률 분석 모듈
- 현재까지의 진행 상황 분석
- 매월 평균 상환액 계산
- 5년 목표 달성 가능성 예측
"""

from datetime import date, datetime
from typing import List, Dict
from src.services.loan_repository import get_active_loans, get_all_loans
from src.services.payment_repository import get_all_payments


# 5년 운영 시작점 (2026.05 기준)
PROJECT_START_DATE = "2026-05-01"
PROJECT_END_DATE = "2031-04-30"  # 5년 후
TARGET_BALANCE = 19_820_000  # 5년 목표 잔액 (1,982만원)


def get_total_balance() -> float:
    """현재 모든 진행 중인 대출의 잔액 합계"""
    loans = get_active_loans()
    return sum(loan.current_balance for loan in loans)


def get_total_initial() -> float:
    """모든 대출의 최초 금액 합계 (완납 포함)"""
    all_loans = get_all_loans()
    return sum(loan.initial_amount for loan in all_loans)


def get_total_repaid() -> float:
    """현재까지 누적 상환액"""
    return get_total_initial() - get_total_balance()


def get_monthly_balance_history() -> List[Dict]:
    """
    월별 잔액 변화 이력
    
    Returns:
        [
            {'month': '2026-05', 'balance': 379563681, 'repaid': 75436319},
            {'month': '2026-06', 'balance': 377000000, 'repaid': 78000000},
            ...
        ]
    """
    all_payments = get_all_payments()
    
    # 시작 시점의 총 잔액
    total_initial = get_total_initial()
    
    # 월별로 그룹핑
    monthly_data = {}
    
    for payment in all_payments:
        try:
            payment_date = datetime.strptime(payment.payment_date, "%Y-%m-%d")
            month_key = payment_date.strftime("%Y-%m")
            
            if month_key not in monthly_data:
                monthly_data[month_key] = {
                    'principal': 0,
                    'interest': 0,
                }
            
            monthly_data[month_key]['principal'] += payment.principal_amount
            monthly_data[month_key]['interest'] += payment.interest_amount
        except:
            continue
    
    # 정렬된 월 리스트
    sorted_months = sorted(monthly_data.keys())
    
    if not sorted_months:
        # 상환 이력 없음 - 현재 시점만
        today = date.today()
        current_month = today.strftime("%Y-%m")
        return [{
            'month': current_month,
            'balance': get_total_balance(),
            'repaid': get_total_repaid(),
            'monthly_principal': 0,
            'monthly_interest': 0,
        }]
    
    # 월별 누적 잔액 계산
    history = []
    cumulative_principal = 0
    
    # 첫 달 시작 시점의 잔액
    start_balance = total_initial
    
    for month in sorted_months:
        monthly = monthly_data[month]
        cumulative_principal += monthly['principal']
        
        balance_at_end = start_balance - cumulative_principal
        
        history.append({
            'month': month,
            'balance': balance_at_end,
            'repaid': cumulative_principal,
            'monthly_principal': monthly['principal'],
            'monthly_interest': monthly['interest'],
        })
    
    return history


def calculate_average_monthly_repayment(months_to_consider: int = 6) -> float:
    """
    최근 N개월 평균 월 상환액 (원금 기준)
    
    Args:
        months_to_consider: 평균 계산에 사용할 최근 개월 수
    """
    history = get_monthly_balance_history()
    
    if not history:
        return 0
    
    # 최근 N개월
    recent = history[-months_to_consider:]
    
    if not recent:
        return 0
    
    total_principal = sum(h['monthly_principal'] for h in recent)
    
    return total_principal / len(recent)


def estimate_target_completion() -> Dict:
    """
    현재 페이스로 5년 목표 달성 가능성 예측
    
    Returns:
        {
            'current_balance': 현재 잔액,
            'target_balance': 목표 잔액 (1,982만원),
            'remaining': 남은 상환액,
            'avg_monthly_repayment': 최근 월 평균 상환,
            'months_at_current_pace': 현재 페이스로 목표까지 개월,
            'months_to_target_date': 5년 목표일까지 남은 개월,
            'will_achieve': 목표 달성 가능 여부 (bool),
            'shortfall': 부족분 (있을 경우),
            'projected_balance_at_target': 5년 후 예상 잔액,
        }
    """
    current_balance = get_total_balance()
    remaining = current_balance - TARGET_BALANCE
    
    avg_monthly = calculate_average_monthly_repayment(months_to_consider=6)
    
    # 5년 목표일까지 남은 개월
    today = date.today()
    target_end = datetime.strptime(PROJECT_END_DATE, "%Y-%m-%d").date()
    months_to_target = max(0, (target_end.year - today.year) * 12 + (target_end.month - today.month))
    
    if avg_monthly > 0 and remaining > 0:
        months_at_pace = remaining / avg_monthly
        will_achieve = months_at_pace <= months_to_target
        shortfall = max(0, remaining - (avg_monthly * months_to_target))
        projected = max(TARGET_BALANCE, current_balance - (avg_monthly * months_to_target))
    else:
        months_at_pace = float('inf')
        will_achieve = False
        shortfall = remaining
        projected = current_balance
    
    return {
        'current_balance': current_balance,
        'target_balance': TARGET_BALANCE,
        'remaining': remaining,
        'avg_monthly_repayment': avg_monthly,
        'months_at_current_pace': months_at_pace,
        'months_to_target_date': months_to_target,
        'will_achieve': will_achieve,
        'shortfall': shortfall,
        'projected_balance_at_target': projected,
    }


def get_projection_data(months_ahead: int = 60) -> List[Dict]:
    """
    향후 N개월 예상 잔액 (현재 페이스 기준)
    
    Returns:
        [
            {'month': '2026-06', 'projected_balance': 377000000},
            {'month': '2026-07', 'projected_balance': 374500000},
            ...
        ]
    """
    current_balance = get_total_balance()
    avg_monthly = calculate_average_monthly_repayment(months_to_consider=6)
    
    today = date.today()
    projections = []
    
    for i in range(1, months_ahead + 1):
        # i개월 후
        future_year = today.year + (today.month + i - 1) // 12
        future_month = ((today.month + i - 1) % 12) + 1
        
        projected_balance = max(0, current_balance - (avg_monthly * i))
        
        projections.append({
            'month': f"{future_year:04d}-{future_month:02d}",
            'projected_balance': projected_balance,
        })
    
    return projections


def get_loan_breakdown_history() -> Dict:
    """
    각 대출별 잔액 변화 이력
    
    Returns:
        {
            '신용대출2': [{'month': '2026-05', 'balance': 60037000}, ...],
            '신용대출1': [{'month': '2026-05', 'balance': 28250100}, ...],
            ...
        }
    """
    all_loans = get_all_loans()
    all_payments = get_all_payments()
    
    breakdown = {}
    
    for loan in all_loans:
        # 해당 대출의 상환 이력
        loan_payments = [p for p in all_payments if p.loan_id == loan.loan_id]
        loan_payments.sort(key=lambda p: p.payment_date)
        
        # 월별 그룹핑
        monthly = {}
        for p in loan_payments:
            try:
                payment_date = datetime.strptime(p.payment_date, "%Y-%m-%d")
                month_key = payment_date.strftime("%Y-%m")
                
                if month_key not in monthly:
                    monthly[month_key] = 0
                
                monthly[month_key] += p.principal_amount
            except:
                continue
        
        # 누적 잔액 계산
        history = []
        cumulative = 0
        
        for month in sorted(monthly.keys()):
            cumulative += monthly[month]
            history.append({
                'month': month,
                'balance': loan.initial_amount - cumulative,
                'repaid_this_month': monthly[month],
            })
        
        breakdown[loan.loan_name] = history
    
    return breakdown