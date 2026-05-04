"""
부분 상환 입력 화면 (Streamlit)
- 폼 밖에 입력 위젯 → 실시간 시뮬레이션
- 폼 안에 저장 버튼만 → 명시적 저장
"""

import streamlit as st
from datetime import date, datetime
from src.services.loan_repository import get_active_loans, get_loan_by_id
from src.services.payment_repository import (
    add_partial_payment,
    get_payments_by_loan,
    get_total_repaid,
)
from src.models.payment import PAYMENT_SOURCES
from src.utils.helpers import format_currency


def calculate_monthly_interest_savings(loan, repayment_amount):
    """월 이자 절감액 계산"""
    monthly_rate = loan.interest_rate / 100 / 12
    return repayment_amount * monthly_rate


def render_payment_form():
    """부분 상환 입력 폼 렌더링"""
    
    st.title("💸 부분 상환 입력")
    st.caption("이자율이 높은 대출부터 우선 상환하면 이자 절감 효과가 큽니다.")
    
    # 진행 중인 대출 가져오기
    loans = get_active_loans()
    
    if not loans:
        st.warning("⚠️ 진행 중인 대출이 없습니다.")
        return
    
    # 대출 선택 옵션
    loan_options = {}
    for loan in loans:
        rate_emoji = "🔴" if loan.interest_rate >= 5 else ("🟡" if loan.interest_rate >= 4 else "🟢")
        label = f"{rate_emoji} {loan.loan_name} ({loan.interest_rate}%, 잔액 {format_currency(loan.current_balance)})"
        loan_options[label] = loan.loan_id
    
    # 추천 표시
    if loans:
        recommended = loans[0]
        st.info(
            f"💡 **추천 우선 상환**: {recommended.loan_name} "
            f"(이자율 {recommended.interest_rate}% - 가장 높음)"
        )
    
    st.divider()
    
    # =========================================
    # 폼 밖: 실시간 입력 위젯 (시뮬레이션 반응)
    # =========================================
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 대출 선택
        selected_label = st.selectbox(
            "💳 대출 선택",
            options=list(loan_options.keys()),
            index=0,
            help="이자율이 높은 대출부터 우선 상환을 추천합니다.",
            key="loan_select"
        )
        selected_loan_id = loan_options[selected_label]
        selected_loan = get_loan_by_id(selected_loan_id)
        
        st.metric(
            label="📊 현재 잔액",
            value=format_currency(selected_loan.current_balance)
        )
    
    with col2:
        # 상환일
        payment_date = st.date_input(
            "📅 상환일",
            value=date.today(),
            max_value=date.today(),
            help="실제로 상환한 날짜를 선택하세요.",
            key="payment_date"
        )
        
        # 누적 상환액
        already_repaid = selected_loan.initial_amount - selected_loan.current_balance
        st.metric(
            label="📈 이미 상환한 금액",
            value=format_currency(already_repaid)
        )
    
    st.divider()
    
    # 상환 금액 입력 (실시간 반응!)
    st.markdown("### 💰 상환 금액 입력")
    
    col_amount1, col_amount2 = st.columns([3, 1])
    
    with col_amount1:
        amount = st.number_input(
            "상환 금액 (원)",
            min_value=0,
            max_value=int(selected_loan.current_balance),
            step=100000,
            help=f"최대 {format_currency(selected_loan.current_balance)} 까지 가능",
            key="amount_input",
            label_visibility="collapsed"
        )
    
    with col_amount2:
        st.markdown("**빠른 입력 예시**")
        st.caption("100만원 = 1000000")
    
    # =========================================
    # 실시간 시뮬레이션 (자동 표시!)
    # =========================================
    
    if amount > 0:
        st.divider()
        st.markdown("### 📊 시뮬레이션 결과 (실시간)")
        
        sim_col1, sim_col2, sim_col3 = st.columns(3)
        
        new_balance = selected_loan.current_balance - amount
        monthly_savings = calculate_monthly_interest_savings(selected_loan, amount)
        
        with sim_col1:
            st.metric(
                label="상환 후 잔액",
                value=format_currency(new_balance),
                delta=f"-{format_currency(amount)}",
                delta_color="inverse"
            )
        
        with sim_col2:
            st.metric(
                label="월 이자 절감",
                value=format_currency(monthly_savings),
                help=f"{selected_loan.interest_rate}% 기준 매월 줄어드는 이자"
            )
        
        with sim_col3:
            # 만기까지 절감액 추정
            if selected_loan.maturity_date:
                try:
                    maturity = datetime.strptime(selected_loan.maturity_date, "%Y-%m-%d")
                    today_dt = datetime.combine(date.today(), datetime.min.time())
                    months_left = max(0, (maturity.year - today_dt.year) * 12 + (maturity.month - today_dt.month))
                    total_savings = monthly_savings * months_left
                    st.metric(
                        label=f"만기까지 절감 (약 {months_left}개월)",
                        value=format_currency(total_savings)
                    )
                except:
                    st.metric(label="만기까지 절감", value="-")
            else:
                st.metric(label="만기까지 절감", value="-")
        
        # 진행률 변화 표시
        new_progress = ((selected_loan.initial_amount - new_balance) / selected_loan.initial_amount) * 100
        current_progress = selected_loan.get_progress_percent()
        
        progress_col1, progress_col2 = st.columns(2)
        
        with progress_col1:
            st.markdown(f"**현재 상환률**: {current_progress:.1f}%")
            st.progress(current_progress / 100)
        
        with progress_col2:
            st.markdown(f"**상환 후 상환률**: {new_progress:.1f}% (+{new_progress - current_progress:.1f}%p)")
            st.progress(new_progress / 100)
        
        # 알림 메시지
        if new_balance == 0:
            st.success(f"🎉 **이 상환으로 {selected_loan.loan_name}이(가) 완납됩니다!**")
        elif new_balance < selected_loan.initial_amount * 0.1:
            st.success(f"💪 잔액이 10% 미만입니다! 거의 다 갚으셨어요.")
        elif new_progress > 50 and current_progress <= 50:
            st.success(f"🎯 절반을 넘어섰어요! 이제 후반전입니다.")
    
    st.divider()
    
    # =========================================
    # 폼 안: 추가 정보 + 저장 버튼만
    # =========================================
    
    st.markdown("### 📝 추가 정보 및 저장")
    
    with st.form("partial_payment_form", clear_on_submit=True):
        col_source1, col_source2 = st.columns(2)
        
        with col_source1:
            source = st.selectbox(
                "💼 자금 출처 (선택)",
                options=[""] + PAYMENT_SOURCES,
                help="이 자금이 어디서 왔는지 기록"
            )
        
        with col_source2:
            created_by = st.selectbox(
                "👤 입력자",
                options=["대표님", "남편"]
            )
        
        memo = st.text_area(
            "📝 메모 (선택)",
            placeholder="예: 5월 보너스로 신용대출2 우선 상환",
            max_chars=200
        )
        
        # 제출 버튼
        col_btn1, col_btn2 = st.columns([3, 1])
        with col_btn2:
            submitted = st.form_submit_button(
                "💾 저장",
                type="primary",
                use_container_width=True
            )
        
        with col_btn1:
            if amount == 0:
                st.warning("⚠️ 상환 금액을 0보다 크게 입력해주세요.")
            else:
                st.caption(f"✅ {format_currency(amount)} 저장 준비 완료. [💾 저장] 버튼을 클릭하세요.")
        
        # 저장 처리
        if submitted:
            if amount <= 0:
                st.error("❌ 상환 금액을 0보다 크게 입력해주세요.")
                return
            
            with st.spinner("저장 중..."):
                result = add_partial_payment(
                    loan_id=selected_loan_id,
                    amount=amount,
                    payment_date=str(payment_date),
                    source=source,
                    memo=memo,
                    created_by=created_by
                )
            
            if result['success']:
                st.success(result['message'])
                st.balloons()
                
                payment = result['payment']
                loan = result['loan']
                
                st.markdown("### 📋 저장된 정보")
                col_r1, col_r2, col_r3 = st.columns(3)
                with col_r1:
                    st.metric("상환 금액", format_currency(payment.principal_amount))
                with col_r2:
                    st.metric("상환 후 잔액", format_currency(payment.balance_after))
                with col_r3:
                    st.metric("진행률", f"{loan.get_progress_percent():.1f}%")
                
                st.info("💡 대시보드에서 갱신된 정보를 확인하세요!")
                
                if loan.status == "완납":
                    st.balloons()
                    st.success(f"🎉🎉🎉 축하합니다! {loan.loan_name}이(가) 완납되었습니다!")
            else:
                st.error(result['message'])
    
    # =========================================
    # 최근 상환 이력
    # =========================================
    st.divider()
    
    with st.expander(f"📜 최근 상환 이력 - {selected_loan.loan_name}"):
        recent_payments = get_payments_by_loan(selected_loan_id)
        
        if not recent_payments:
            st.caption("아직 상환 이력이 없습니다.")
        else:
            st.caption(f"총 {len(recent_payments)}건의 상환 이력")
            
            for p in recent_payments[:10]:
                col_p1, col_p2, col_p3, col_p4 = st.columns([2, 2, 2, 3])
                
                with col_p1:
                    st.markdown(f"**{p.payment_date}**")
                
                with col_p2:
                    st.markdown(f"💰 {format_currency(p.principal_amount)}")
                
                with col_p3:
                    if p.source:
                        st.caption(f"💼 {p.source}")
                    else:
                        st.caption("-")
                
                with col_p4:
                    if p.memo:
                        st.caption(f"📝 {p.memo[:30]}{'...' if len(p.memo) > 30 else ''}")


if __name__ == "__main__":
    render_payment_form()