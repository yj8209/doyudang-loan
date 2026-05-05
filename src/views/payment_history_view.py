"""
상환 이력 관리 화면 (Streamlit)
- 전체 상환 이력 조회
- 필터링 (대출/종류/기간)
- 수정 / 삭제 (잔액 자동 보정)
"""

import streamlit as st
from datetime import date
from src.services.loan_repository import get_active_loans, get_loan_by_id
from src.services.payment_repository import (
    get_all_payments,
    get_payments_with_filters,
    get_payment_by_id,
    update_payment,
    delete_payment,
)
from src.models.payment import PAYMENT_TYPES, PAYMENT_SOURCES
from src.utils.helpers import format_currency


def render_payment_history():
    """상환 이력 관리 화면"""
    
    st.title("📜 상환 이력 관리")
    st.caption("입력한 상환 이력을 확인하고, 잘못된 데이터를 수정/삭제할 수 있습니다.")
    
    # 모든 대출
    loans = get_active_loans()
    
    # =========================================
    # 필터
    # =========================================
    st.divider()
    st.markdown("### 🔍 필터")
    
    filter_col1, filter_col2, filter_col3 = st.columns(3)
    
    with filter_col1:
        loan_filter_options = {"전체": None}
        for loan in loans:
            loan_filter_options[loan.loan_name] = loan.loan_id
        
        selected_loan_label = st.selectbox(
            "대출",
            options=list(loan_filter_options.keys())
        )
        loan_filter = loan_filter_options[selected_loan_label]
    
    with filter_col2:
        type_options = ["전체"] + PAYMENT_TYPES
        type_filter = st.selectbox(
            "종류",
            options=type_options
        )
        if type_filter == "전체":
            type_filter = None
    
    with filter_col3:
        period_options = {
            "전체 기간": None,
            "최근 7일": 7,
            "최근 30일": 30,
            "최근 90일": 90,
            "최근 1년": 365,
        }
        period_label = st.selectbox(
            "기간",
            options=list(period_options.keys()),
            index=0
        )
        period_filter = period_options[period_label]
    
    # =========================================
    # 필터링된 결과
    # =========================================
    filtered_payments = get_payments_with_filters(
        loan_id=loan_filter,
        payment_type=type_filter,
        days_back=period_filter
    )
    
    st.divider()
    st.markdown(f"### 📊 상환 이력 ({len(filtered_payments)}건)")
    
    if not filtered_payments:
        st.info("ℹ️ 조건에 맞는 상환 이력이 없습니다.")
        return
    
    # 통계 요약
    total_principal = sum(p.principal_amount for p in filtered_payments)
    total_interest = sum(p.interest_amount for p in filtered_payments)
    total_overdue = sum(p.overdue_interest for p in filtered_payments)
    
    stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
    
    with stat_col1:
        st.metric("총 건수", f"{len(filtered_payments)}건")
    
    with stat_col2:
        st.metric("원금 합계", format_currency(total_principal))
    
    with stat_col3:
        st.metric("이자 합계", format_currency(total_interest))
    
    with stat_col4:
        st.metric("총합", format_currency(total_principal + total_interest + total_overdue))
    
    st.divider()
    
    # =========================================
    # 상환 이력 목록
    # =========================================
    for payment in filtered_payments:
        loan = get_loan_by_id(payment.loan_id)
        loan_name = loan.loan_name if loan else "알 수 없음"
        
        # 종류별 이모지
        type_emoji = {
            "부분상환": "💸",
            "정기상환": "📋",
            "이자납부": "💰",
            "만기상환": "🏁",
            "일부상환": "💵",
        }.get(payment.payment_type, "📄")
        
        # 테스트 표시
        is_test = payment.memo and ("테스트" in payment.memo.lower() or "test" in payment.memo.lower())
        test_badge = " ⚠️ 테스트" if is_test else ""
        
        with st.container(border=True):
            # 헤더
            header_col1, header_col2 = st.columns([4, 1])
            
            with header_col1:
                st.markdown(
                    f"### {type_emoji} {payment.payment_date} | "
                    f"**{loan_name}** | {payment.payment_type}{test_badge}"
                )
            
            with header_col2:
                # 액션 버튼
                action = st.selectbox(
                    "액션",
                    options=["선택", "📝 수정", "🗑 삭제"],
                    key=f"action_{payment.payment_id}",
                    label_visibility="collapsed"
                )
            
            # 정보 그리드
            info_col1, info_col2, info_col3, info_col4 = st.columns(4)
            
            with info_col1:
                if payment.principal_amount > 0:
                    st.markdown(f"**💰 원금**\n\n{format_currency(payment.principal_amount)}")
                else:
                    st.markdown(f"**💰 원금**\n\n0원")
            
            with info_col2:
                if payment.interest_amount > 0:
                    st.markdown(f"**💸 이자**\n\n{format_currency(payment.interest_amount)}")
                else:
                    st.markdown(f"**💸 이자**\n\n0원")
            
            with info_col3:
                st.markdown(f"**📊 잔액**\n\n{format_currency(payment.balance_after)}")
            
            with info_col4:
                st.markdown(f"**👤 입력자**\n\n{payment.created_by or '미입력'}")
            
            # 추가 정보
            details = []
            if payment.source:
                details.append(f"💼 자금: {payment.source}")
            if payment.memo:
                details.append(f"📝 메모: {payment.memo}")
            
            if details:
                st.caption(" | ".join(details))
            
            # =========================================
            # 액션 처리
            # =========================================
            if action == "📝 수정":
                with st.form(f"edit_form_{payment.payment_id}"):
                    st.markdown("##### 📝 상환 이력 수정")
                    st.warning("⚠️ 원금 수정 시 대출 잔액이 자동으로 보정됩니다.")
                    
                    edit_col1, edit_col2 = st.columns(2)
                    
                    with edit_col1:
                        new_date = st.date_input(
                            "상환일",
                            value=date.fromisoformat(payment.payment_date),
                            max_value=date.today()
                        )
                        
                        new_principal = st.number_input(
                            "원금 (원)",
                            min_value=0.0,
                            value=float(payment.principal_amount),
                            step=1000.0
                        )
                    
                    with edit_col2:
                        new_interest = st.number_input(
                            "이자 (원)",
                            min_value=0.0,
                            value=float(payment.interest_amount),
                            step=1000.0
                        )
                        
                        new_source = st.selectbox(
                            "자금 출처",
                            options=[""] + PAYMENT_SOURCES,
                            index=([""] + PAYMENT_SOURCES).index(payment.source) if payment.source in [""] + PAYMENT_SOURCES else 0
                        )
                    
                    new_memo = st.text_area(
                        "메모",
                        value=payment.memo or "",
                        max_chars=500
                    )
                    
                    changed_by = st.selectbox(
                        "처리자",
                        options=["대표님", "남편"],
                        key=f"by_edit_{payment.payment_id}"
                    )
                    
                    submitted = st.form_submit_button(
                        "💾 수정 확정",
                        type="primary",
                        use_container_width=True
                    )
                    
                    if submitted:
                        with st.spinner("수정 중..."):
                            result = update_payment(
                                payment_id=payment.payment_id,
                                new_principal=new_principal,
                                new_interest=new_interest,
                                new_date=str(new_date),
                                new_source=new_source,
                                new_memo=new_memo,
                                changed_by=changed_by
                            )
                        
                        if result['success']:
                            st.success(result['message'])
                            st.balloons()
                            st.info("💡 페이지를 새로고침하면 갱신된 정보가 표시됩니다.")
                        else:
                            st.error(result['message'])
            
            elif action == "🗑 삭제":
                with st.form(f"delete_form_{payment.payment_id}"):
                    st.markdown("##### 🗑 상환 이력 삭제")
                    st.error(
                        f"⚠️ **주의!** 이 상환 이력을 삭제하면:\n"
                        f"- 원금 {format_currency(payment.principal_amount)}이 잔액에 다시 더해집니다.\n"
                        f"- 이 작업은 되돌릴 수 없습니다.\n"
                        f"- 잔액 변경: {format_currency(loan.current_balance if loan else 0)} → "
                        f"{format_currency((loan.current_balance if loan else 0) + payment.principal_amount)}"
                    )
                    
                    confirm = st.checkbox(
                        f"✅ 위 내용을 확인했고, 삭제에 동의합니다.",
                        key=f"confirm_{payment.payment_id}"
                    )
                    
                    reason = st.text_input(
                        "삭제 사유",
                        placeholder="예: 테스트 데이터 정리, 잘못된 입력 정정",
                        key=f"reason_{payment.payment_id}"
                    )
                    
                    changed_by = st.selectbox(
                        "처리자",
                        options=["대표님", "남편"],
                        key=f"by_del_{payment.payment_id}"
                    )
                    
                    submitted = st.form_submit_button(
                        "🗑 삭제 확정",
                        type="primary",
                        use_container_width=True
                    )
                    
                    if submitted:
                        if not confirm:
                            st.error("❌ 동의 체크박스를 체크해주세요.")
                        else:
                            with st.spinner("삭제 중..."):
                                result = delete_payment(
                                    payment_id=payment.payment_id,
                                    reason=reason,
                                    changed_by=changed_by
                                )
                            
                            if result['success']:
                                st.success(result['message'])
                                st.balloons()
                                st.info("💡 페이지를 새로고침하면 갱신된 정보가 표시됩니다.")
                            else:
                                st.error(result['message'])


if __name__ == "__main__":
    render_payment_history()