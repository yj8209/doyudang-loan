"""
신규 대출 추가 화면 (Streamlit)
- 모든 필드 입력 폼
- 검증 로직
- Drive에 저장 + 변경 이력 추적
"""

import streamlit as st
from datetime import date, datetime
from src.models.loan import (
    Loan,
    LOAN_TYPES,
    REPAYMENT_METHODS,
    RATE_TYPES,
)
from src.services.loan_repository import add_new_loan
from src.utils.helpers import format_currency


def render_new_loan_form():
    """신규 대출 추가 화면"""
    
    st.title("🆕 신규 대출 추가")
    st.caption("새로운 대출을 등록합니다. 모든 필수 항목을 정확하게 입력해주세요.")
    
    # 안내
    st.info("""
    💡 **입력 가이드**
    - 우리은행 대출 약정서 또는 인터넷뱅킹 대출 상세 정보를 참고하세요.
    - 모든 항목은 정확하게 입력해야 5년 운영 데이터가 정확합니다.
    - 변경 가능: 등록 후에도 만기 연장, 금리 변경 등 수정 가능합니다.
    """)
    
    st.divider()
    
    with st.form("new_loan_form", clear_on_submit=False):
        
        # =========================================
        # 기본 정보
        # =========================================
        st.markdown("### 📌 기본 정보")
        
        col1, col2 = st.columns(2)
        
        with col1:
            loan_name = st.text_input(
                "대출명 *",
                placeholder="예: 신용대출3 - 신한 마이카대출",
                help="대출을 식별할 수 있는 명확한 이름"
            )
            
            loan_type = st.selectbox(
                "대출 종류 *",
                options=LOAN_TYPES,
                index=0
            )
            
            bank_name = st.text_input(
                "은행명 *",
                value="우리은행",
                placeholder="예: 우리은행, 국민은행, 신한은행"
            )
            
            branch = st.text_input(
                "지점명",
                placeholder="예: 오리역지점, 대치역금융센터"
            )
        
        with col2:
            account_number = st.text_input(
                "계좌번호 *",
                placeholder="예: 1200-904-840811"
            )
            
            repayment_method = st.selectbox(
                "상환방식 *",
                options=REPAYMENT_METHODS,
                index=0,
                help="만기일시: 매월 이자만, 만기일 원금 일시상환 / 원리금균등: 매월 원금+이자 균등 차감"
            )
            
            payment_day = st.number_input(
                "매월 이체일 *",
                min_value=1,
                max_value=31,
                value=10,
                step=1,
                help="매월 자동이체 일자"
            )
        
        st.divider()
        
        # =========================================
        # 금액 정보
        # =========================================
        st.markdown("### 💰 금액 정보")
        
        col_amount1, col_amount2 = st.columns(2)
        
        with col_amount1:
            initial_amount = st.number_input(
                "최초 대출 금액 (원) *",
                min_value=0,
                value=10000000,
                step=1000000,
                help="대출 약정서상 최초 금액"
            )
        
        with col_amount2:
            current_balance = st.number_input(
                "현재 잔액 (원) *",
                min_value=0,
                value=10000000,
                step=100000,
                help="현재 남은 잔액 (최초 금액과 같으면 신규)"
            )
        
        # 진행률 미리보기
        if initial_amount > 0:
            progress = ((initial_amount - current_balance) / initial_amount) * 100
            st.caption(f"📊 현재 진행률: **{progress:.1f}%** 상환됨")
            st.progress(progress / 100)
        
        st.divider()
        
        # =========================================
        # 기간 정보
        # =========================================
        st.markdown("### 📅 기간 정보")
        
        col_date1, col_date2 = st.columns(2)
        
        with col_date1:
            start_date_input = st.date_input(
                "대출 시작일 *",
                value=date.today(),
                help="대출 약정 시작일"
            )
        
        with col_date2:
            # 기본 만기일: 1년 후
            try:
                default_maturity = date(date.today().year + 1, date.today().month, date.today().day)
            except ValueError:
                default_maturity = date(date.today().year + 1, date.today().month, 28)
            
            maturity_date_input = st.date_input(
                "만기일 *",
                value=default_maturity,
                help="대출 만기일 (만기일시 대출은 이때 일시 상환)"
            )
        
        # 대출 기간 계산
        if maturity_date_input > start_date_input:
            days_total = (maturity_date_input - start_date_input).days
            years = days_total / 365
            st.caption(f"📅 대출 기간: 약 **{years:.1f}년** ({days_total}일)")
        
        st.divider()
        
        # =========================================
        # 금리 정보
        # =========================================
        st.markdown("### 💯 금리 정보")
        
        col_rate1, col_rate2 = st.columns(2)
        
        with col_rate1:
            interest_rate = st.number_input(
                "현재 적용 금리 (%) *",
                min_value=0.0,
                max_value=30.0,
                value=4.5,
                step=0.01,
                format="%.2f",
                help="현재 적용되는 연이율"
            )
            
            rate_type = st.selectbox(
                "금리 종류 *",
                options=RATE_TYPES,
                index=0,
                help="고정: 만기까지 동일 / 변동: 기준금리 변동에 따라 변동"
            )
        
        with col_rate2:
            rate_base = st.text_input(
                "기준금리 (변동인 경우)",
                placeholder="예: KORIBOR 3개월, COFIX 6개월",
                help="변동금리의 기준이 되는 금리"
            )
            
            rate_spread = st.number_input(
                "가산금리 (%)",
                min_value=0.0,
                max_value=10.0,
                value=0.0,
                step=0.01,
                format="%.2f",
                help="기준금리 + 가산금리 = 적용 금리"
            )
        
        # 금리 검증
        if rate_type == "변동" and rate_base and rate_spread > 0:
            st.caption(f"💡 변동금리: {rate_base} + {rate_spread}% = 현재 {interest_rate}%")
        
        st.divider()
        
        # =========================================
        # 메타 정보
        # =========================================
        st.markdown("### 📝 추가 정보")
        
        memo = st.text_area(
            "메모 (선택)",
            placeholder="대출 용도, 특이사항 등을 자유롭게 기록하세요.",
            max_chars=500,
            height=100
        )
        
        col_meta1, col_meta2 = st.columns([1, 3])
        
        with col_meta1:
            created_by = st.selectbox(
                "👤 등록자",
                options=["대표님", "남편"]
            )
        
        st.divider()
        
        # =========================================
        # 등록 버튼
        # =========================================
        col_btn1, col_btn2 = st.columns([3, 1])
        
        with col_btn1:
            st.caption("⚠️ 모든 필수 항목(*)을 정확하게 입력했는지 확인하세요.")
        
        with col_btn2:
            submitted = st.form_submit_button(
                "💾 신규 등록",
                type="primary",
                use_container_width=True
            )
        
        # =========================================
        # 등록 처리
        # =========================================
        if submitted:
            # 클라이언트 측 검증
            errors = []
            
            if not loan_name.strip():
                errors.append("❌ 대출명을 입력해주세요.")
            
            if not bank_name.strip():
                errors.append("❌ 은행명을 입력해주세요.")
            
            if not account_number.strip():
                errors.append("❌ 계좌번호를 입력해주세요.")
            
            if initial_amount <= 0:
                errors.append("❌ 최초 금액은 0보다 커야 합니다.")
            
            if current_balance > initial_amount:
                errors.append("❌ 현재 잔액이 최초 금액보다 클 수 없습니다.")
            
            if interest_rate <= 0:
                errors.append("❌ 금리는 0보다 커야 합니다.")
            
            if maturity_date_input <= start_date_input:
                errors.append("❌ 만기일은 시작일 이후여야 합니다.")
            
            if rate_type == "변동" and not rate_base.strip():
                errors.append("❌ 변동금리는 기준금리를 입력해주세요.")
            
            if errors:
                for error in errors:
                    st.error(error)
            else:
                # Loan 객체 생성
                new_loan = Loan(
                    loan_name=loan_name.strip(),
                    bank_name=bank_name.strip(),
                    account_number=account_number.strip(),
                    loan_type=loan_type,
                    repayment_method=repayment_method,
                    initial_amount=float(initial_amount),
                    current_balance=float(current_balance),
                    start_date=str(start_date_input),
                    maturity_date=str(maturity_date_input),
                    payment_day=int(payment_day),
                    interest_rate=float(interest_rate),
                    rate_type=rate_type,
                    rate_base=rate_base.strip(),
                    rate_spread=float(rate_spread),
                    branch=branch.strip(),
                    status="진행중",
                    memo=memo.strip(),
                )
                
                # 저장
                with st.spinner("저장 중..."):
                    result = add_new_loan(new_loan, changed_by=created_by)
                
                if result['success']:
                    st.success(result['message'])
                    st.balloons()
                    
                    # 결과 표시
                    saved_loan = result['loan']
                    
                    st.markdown("### 📋 등록된 대출 정보")
                    
                    res_col1, res_col2, res_col3 = st.columns(3)
                    
                    with res_col1:
                        st.metric("최초 금액", format_currency(saved_loan.initial_amount))
                    
                    with res_col2:
                        st.metric("현재 잔액", format_currency(saved_loan.current_balance))
                    
                    with res_col3:
                        st.metric("금리", f"{saved_loan.interest_rate}% ({saved_loan.rate_type})")
                    
                    st.info(
                        f"💡 **{saved_loan.loan_name}** 대출이 성공적으로 등록되었습니다!\n\n"
                        f"- 대시보드에서 갱신된 정보를 확인하세요.\n"
                        f"- 정기상환/부분상환 입력 시 사용 가능합니다.\n"
                        f"- 시뮬레이터에서도 자동으로 포함됩니다."
                    )
                else:
                    st.error(result['message'])


if __name__ == "__main__":
    render_new_loan_form()