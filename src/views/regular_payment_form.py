"""
정기상환 확정 화면 (Streamlit)
- 매월 자동으로 차감되는 정기상환 처리
- 만기일시: 이자만 입력
- 원리금균등: 원금 + 이자 분리 입력
"""

import streamlit as st
from datetime import date, datetime
from src.services.loan_repository import get_active_loans, get_loan_by_id
from src.services.payment_repository import (
    add_regular_payment,
    get_recent_regular_payments,
    estimate_monthly_payment,
    estimate_monthly_interest,
)
from src.utils.helpers import format_currency


def get_payment_status(loan, today):
    """이번 달 정기상환 상태 판단"""
    payment_day = loan.payment_day
    today_day = today.day
    
    # 이번 달 이체일이 지났는지
    if today_day > payment_day:
        return "이체일 지남 - 입력 가능"
    elif today_day == payment_day:
        return "오늘 이체일! 입력 권장"
    else:
        days_until = payment_day - today_day
        return f"{days_until}일 후 이체일"


def get_status_color(status):
    """상태별 색상 이모지"""
    if "오늘" in status:
        return "🔴"
    elif "지남" in status:
        return "🟡"
    else:
        return "🟢"


def render_regular_payment_form():
    """정기상환 확정 화면"""
    
    st.title("📋 정기상환 확정")
    st.caption("매월 자동으로 차감되는 정기상환을 우리은행 거래내역 보고 입력하세요.")
    
    # 진행 중인 대출
    loans = get_active_loans()
    
    if not loans:
        st.warning("⚠️ 진행 중인 대출이 없습니다.")
        return
    
    # 이번 달 정보
    today = date.today()
    st.markdown(f"### 📅 이번 달 ({today.year}년 {today.month}월) 정기상환")
    
    # 진행 중인 대출별 카드
    for i, loan in enumerate(loans):
        # 상태 계산
        payment_status = get_payment_status(loan, today)
        status_emoji = get_status_color(payment_status)
        rate_emoji = "🔴" if loan.interest_rate >= 5 else ("🟡" if loan.interest_rate >= 4 else "🟢")
        
        # 컨테이너로 카드 만들기
        with st.container():
            # 헤더
            header_col1, header_col2 = st.columns([4, 1])
            
            with header_col1:
                st.markdown(f"### {rate_emoji} {loan.loan_name}")
                st.caption(
                    f"🏦 {loan.bank_name} ({loan.branch}) | "
                    f"📅 매월 {loan.payment_day}일 자동이체 | "
                    f"💼 {loan.repayment_method} | "
                    f"💯 금리 {loan.interest_rate}%"
                )
            
            with header_col2:
                st.markdown(f"**{status_emoji} {payment_status}**")
            
            # 만기 임박 경고
            if loan.memo and "만기" in loan.memo:
                st.warning(f"⚠️ {loan.memo}")
            
            # 정보 카드
            info_col1, info_col2, info_col3 = st.columns(3)
            
            estimate = estimate_monthly_payment(loan)
            
            with info_col1:
                st.metric(
                    label="현재 잔액",
                    value=format_currency(loan.current_balance)
                )
            
            with info_col2:
                if loan.repayment_method == "만기일시":
                    st.metric(
                        label="예상 이자 (월)",
                        value=format_currency(estimate['expected_interest'])
                    )
                else:
                    st.metric(
                        label="예상 원리금 (월)",
                        value=format_currency(estimate['expected_total']),
                        help=f"원금 {format_currency(estimate['expected_principal'])} + 이자 {format_currency(estimate['expected_interest'])}"
                    )
            
            with info_col3:
                if loan.maturity_date:
                    try:
                        maturity = datetime.strptime(loan.maturity_date, "%Y-%m-%d")
                        today_dt = datetime.combine(today, datetime.min.time())
                        days_left = (maturity - today_dt).days
                        if days_left < 0:
                            st.metric(label="만기", value="지남")
                        elif days_left < 365:
                            st.metric(label="만기까지", value=f"{days_left}일")
                        else:
                            years_left = days_left / 365
                            st.metric(label="만기까지", value=f"약 {years_left:.1f}년")
                    except:
                        st.metric(label="만기", value=loan.maturity_date)
            
            # 입력 폼
            with st.expander(f"✏️ {loan.loan_name} 거래내역 입력", expanded=False):
                with st.form(key=f"regular_payment_{loan.loan_id}", clear_on_submit=True):
                    
                    # 차감 일자
                    # 이번 달 이체일 계산 (미래면 지난 달 이체일 사용)
                    if loan.payment_day <= 28:
                        try:
                            this_month_payment = today.replace(day=loan.payment_day)
                            if this_month_payment > today:
                                if today.month == 1:
                                    default_date = today.replace(year=today.year - 1, month=12, day=loan.payment_day)
                                else:
                                    default_date = today.replace(month=today.month - 1, day=loan.payment_day)
                            else:
                                default_date = this_month_payment
                        except ValueError:
                            default_date = today
                    else:
                        default_date = today
                    
                    payment_date = st.date_input(
                        "📅 차감 일자",
                        value=default_date,
                        max_value=today,
                        key=f"date_{loan.loan_id}"
                    )
                    
                    # 만기일시 vs 원리금균등 분기
                    if loan.repayment_method == "만기일시":
                        st.info(
                            "ℹ️ **만기일시 대출**입니다. "
                            "매월 이자만 차감되고, 원금은 만기일에 일시 상환됩니다."
                        )
                        
                        principal_amount = 0
                        interest_amount = st.number_input(
                            "💸 실제 차감된 이자 (원)",
                            min_value=0,
                            value=int(estimate['expected_interest']),
                            step=1000,
                            help=f"우리은행 거래내역 보고 실제 차감 금액 입력. 예상: {format_currency(estimate['expected_interest'])}",
                            key=f"interest_{loan.loan_id}"
                        )
                        
                    else:  # 원리금균등
                        st.info(
                            "ℹ️ **원리금균등 대출**입니다. "
                            "매월 원금 + 이자가 함께 차감됩니다. "
                            "우리은행 명세서를 보고 원금/이자를 분리해서 입력하세요."
                        )
                        
                        col_p1, col_p2 = st.columns(2)
                        
                        with col_p1:
                            principal_amount = st.number_input(
                                "💰 실제 차감된 원금 (원)",
                                min_value=0,
                                value=int(estimate['expected_principal']),
                                step=1000,
                                help=f"예상: {format_currency(estimate['expected_principal'])}",
                                key=f"principal_{loan.loan_id}"
                            )
                        
                        with col_p2:
                            interest_amount = st.number_input(
                                "💸 실제 차감된 이자 (원)",
                                min_value=0,
                                value=int(estimate['expected_interest']),
                                step=1000,
                                help=f"예상: {format_currency(estimate['expected_interest'])}",
                                key=f"interest_{loan.loan_id}"
                            )
                    
                    # 총액 표시
                    total = principal_amount + interest_amount
                    st.markdown(f"**📊 총 차감액: {format_currency(total)}**")
                    
                    # 입력자 + 메모
                    col_meta1, col_meta2 = st.columns(2)
                    
                    with col_meta1:
                        created_by = st.selectbox(
                            "👤 입력자",
                            options=["대표님", "남편"],
                            key=f"by_{loan.loan_id}"
                        )
                    
                    with col_meta2:
                        st.write("")  # 공백
                    
                    memo = st.text_input(
                        "📝 메모 (선택)",
                        placeholder="예: 5월 정기상환 정상 처리",
                        key=f"memo_{loan.loan_id}"
                    )
                    
                    # 저장 버튼
                    submitted = st.form_submit_button(
                        "💾 정기상환 확정",
                        type="primary",
                        use_container_width=True
                    )
                    
                    if submitted:
                        if total == 0:
                            st.error("❌ 원금 또는 이자 중 하나는 입력해야 합니다.")
                        else:
                            with st.spinner("저장 중..."):
                                result = add_regular_payment(
                                    loan_id=loan.loan_id,
                                    payment_date=str(payment_date),
                                    principal_amount=principal_amount,
                                    interest_amount=interest_amount,
                                    memo=memo,
                                    created_by=created_by
                                )
                            
                            if result['success']:
                                st.success(result['message'])
                                st.balloons()
                                
                                # 결과 메트릭
                                payment = result['payment']
                                updated_loan = result['loan']
                                
                                res_col1, res_col2, res_col3 = st.columns(3)
                                with res_col1:
                                    st.metric("원금 차감", format_currency(payment.principal_amount))
                                with res_col2:
                                    st.metric("이자 차감", format_currency(payment.interest_amount))
                                with res_col3:
                                    st.metric(
                                        "갱신된 잔액",
                                        format_currency(payment.balance_after)
                                    )
                                
                                if updated_loan.status == "완납":
                                    st.balloons()
                                    st.success(f"🎉🎉 {updated_loan.loan_name}이(가) 완납되었습니다!")
                                
                                st.info("💡 대시보드에서 갱신된 정보를 확인하세요!")
                            else:
                                st.error(result['message'])
            
            # 최근 정기상환 이력
            recent_payments = get_recent_regular_payments(loan.loan_id, limit=3)
            if recent_payments:
                with st.expander(f"📜 최근 정기상환 - {loan.loan_name} (최근 {len(recent_payments)}건)"):
                    for p in recent_payments:
                        col_h1, col_h2, col_h3, col_h4 = st.columns([2, 2, 2, 2])
                        
                        with col_h1:
                            st.markdown(f"**{p.payment_date}**")
                        
                        with col_h2:
                            if p.principal_amount > 0:
                                st.caption(f"💰 원금: {format_currency(p.principal_amount)}")
                            else:
                                st.caption("💰 원금: 0원")
                        
                        with col_h3:
                            st.caption(f"💸 이자: {format_currency(p.interest_amount)}")
                        
                        with col_h4:
                            st.caption(f"📊 잔액: {format_currency(p.balance_after)}")
            
            st.divider()
    
    # 사용 안내
    with st.expander("💡 정기상환 입력 가이드"):
        st.markdown("""
        ### 입력 방법
        
        1. **우리은행 앱/홈페이지**에서 거래내역 확인
        2. 해당 대출의 **이체일** 거래 찾기
        3. **출금 금액** 확인:
           - **만기일시 대출** (신용대출): 이자만 차감 → 이자 칸에 입력
           - **원리금균등 대출** (주담대): 원금 + 이자 → 명세서 보고 분리 입력
        4. **[💾 정기상환 확정]** 클릭
        
        ### 예상 금액과 다를 때
        - 변동금리 변경 → 이자가 약간 다를 수 있음
        - 그대로 실제 거래내역 금액 입력
        - 메모에 "변동금리 변경됨" 등 기록
        
        ### 자동 처리 사항
        - ✅ 원금만 잔액에서 차감 (이자는 비용)
        - ✅ 진행률 자동 갱신
        - ✅ 완납 시 자동 처리
        """)


if __name__ == "__main__":
    render_regular_payment_form()