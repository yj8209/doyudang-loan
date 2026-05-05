"""
부분상환 시뮬레이터 - 계산 모듈
- 각 대출별 부분상환 효과 자동 계산
- 단기/장기 절감 효과 비교
- 추천 알고리즘
"""

from datetime import datetime, date
from typing import List, Dict


def calculate_months_until_maturity(loan, today=None) -> int:
    """만기까지 남은 개월 수 계산"""
    if today is None:
        today = date.today()
    
    try:
        maturity = datetime.strptime(loan.maturity_date, "%Y-%m-%d").date()
        if maturity <= today:
            return 0
        
        months = (maturity.year - today.year) * 12 + (maturity.month - today.month)
        return max(0, months)
    except:
        return 0


def calculate_monthly_interest(balance: float, annual_rate: float) -> float:
    """월 이자 계산: 잔액 × 연이율 / 12"""
    return balance * (annual_rate / 100) / 12


def simulate_partial_payment(loan, repayment_amount: float) -> dict:
    """
    특정 대출에 부분상환 시 효과 계산
    
    Returns:
        {
            'loan_id': str,
            'loan_name': str,
            'interest_rate': float,
            'rate_type': str,
            'current_balance': float,
            'new_balance': float,
            'repayment_amount': float,
            'monthly_savings': float,        # 월 이자 절감
            'months_until_maturity': int,    # 만기까지 개월
            'total_savings': float,          # 만기까지 총 절감액
            'maturity_date': str,
            'is_paid_off': bool,             # 완납 여부
            'repayment_method': str,
            'priority_score': float,         # 추천 점수
        }
    """
    # 검증
    if repayment_amount <= 0 or repayment_amount > loan.current_balance:
        repayment_amount = min(repayment_amount, loan.current_balance)
    
    # 새 잔액
    new_balance = loan.current_balance - repayment_amount
    
    # 월 이자 절감
    monthly_savings = calculate_monthly_interest(repayment_amount, loan.interest_rate)
    
    # 만기까지 개월 수
    months_left = calculate_months_until_maturity(loan)
    
    # 만기까지 총 절감액
    total_savings = monthly_savings * months_left
    
    # 추천 점수 계산
    # - 만기 임박(< 6개월): 가산점
    # - 이자율 높음: 가산점
    # - 잔액 큼: 가산점 (장기 효과)
    priority_score = 0
    
    # 1. 이자율 가중치 (가장 중요)
    priority_score += loan.interest_rate * 10
    
    # 2. 만기 임박 시 추가 가산점
    if months_left <= 6 and months_left > 0:
        priority_score += 30  # 만기 임박 보너스
    elif months_left <= 12:
        priority_score += 15
    
    # 3. 변동금리 추가 가산점 (금리 인상 위험)
    if loan.rate_type == "변동":
        priority_score += 5
    
    return {
        'loan_id': loan.loan_id,
        'loan_name': loan.loan_name,
        'interest_rate': loan.interest_rate,
        'rate_type': loan.rate_type,
        'current_balance': loan.current_balance,
        'new_balance': new_balance,
        'repayment_amount': repayment_amount,
        'monthly_savings': monthly_savings,
        'months_until_maturity': months_left,
        'total_savings': total_savings,
        'maturity_date': loan.maturity_date,
        'is_paid_off': new_balance == 0,
        'repayment_method': loan.repayment_method,
        'priority_score': priority_score,
    }


def simulate_all_loans(loans: List, repayment_amount: float) -> List[dict]:
    """모든 대출에 대해 동일 금액 부분상환 시뮬레이션"""
    results = []
    for loan in loans:
        sim = simulate_partial_payment(loan, repayment_amount)
        results.append(sim)
    
    # 추천 점수 높은 순으로 정렬
    results.sort(key=lambda x: x['priority_score'], reverse=True)
    
    return results


def get_recommendation(simulations: List[dict]) -> dict:
    """
    시뮬레이션 결과에서 추천 도출
    
    Returns:
        {
            'best_short_term': dict,      # 단기 효과 최대
            'best_long_term': dict,       # 장기 효과 최대
            'best_overall': dict,         # 종합 추천 (점수 1위)
            'reason': str,                # 추천 이유
        }
    """
    if not simulations:
        return None
    
    # 단기 효과 최대 (월 절감액 기준)
    best_short = max(simulations, key=lambda x: x['monthly_savings'])
    
    # 장기 효과 최대 (총 절감액 기준)
    best_long = max(simulations, key=lambda x: x['total_savings'])
    
    # 종합 추천 (priority score 1위)
    best_overall = simulations[0]  # 이미 정렬됨
    
    # 추천 이유 작성
    reason = ""
    if best_overall['months_until_maturity'] <= 6 and best_overall['months_until_maturity'] > 0:
        reason = f"⚠️ 만기 임박 ({best_overall['months_until_maturity']}개월) + 이자율 {best_overall['interest_rate']}%로 우선 상환 추천"
    elif best_overall['interest_rate'] >= 5:
        reason = f"💰 이자율 {best_overall['interest_rate']}%로 가장 높음. 우선 상환 시 이자 절감 효과가 가장 큼"
    elif best_overall == best_long:
        reason = f"📈 장기적으로 총 {best_overall['total_savings']:,.0f}원의 이자 절감 효과"
    else:
        reason = f"⭐ 이자율 {best_overall['interest_rate']}%, 만기 {best_overall['months_until_maturity']}개월 남음"
    
    return {
        'best_short_term': best_short,
        'best_long_term': best_long,
        'best_overall': best_overall,
        'reason': reason,
    }


def simulate_split_payment(loans: List, total_amount: float, splits: dict) -> dict:
    """
    여러 대출에 분산 상환 시뮬레이션
    
    Args:
        loans: 대출 목록
        total_amount: 총 가용 자금
        splits: {loan_id: ratio} 비율 (합 = 1.0)
    
    Returns:
        {
            'total_amount': float,
            'simulations': List[dict],   # 각 대출별 시뮬레이션
            'total_monthly_savings': float,
            'total_savings': float,
        }
    """
    results = []
    total_monthly = 0
    total_long = 0
    
    for loan in loans:
        ratio = splits.get(loan.loan_id, 0)
        amount = total_amount * ratio
        
        if amount > 0:
            sim = simulate_partial_payment(loan, amount)
            results.append(sim)
            total_monthly += sim['monthly_savings']
            total_long += sim['total_savings']
    
    return {
        'total_amount': total_amount,
        'simulations': results,
        'total_monthly_savings': total_monthly,
        'total_savings': total_long,
    }