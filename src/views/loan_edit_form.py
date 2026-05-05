"""
대출 수정 / 만기 연장 화면 (Streamlit)
- 기존 대출 정보 수정
- 만기 연장 (만기일 + 금리 변경)
- 변경 이력 자동 추적
"""

import streamlit as st
from datetime import date, datetime
from src.models.loan import RATE_TYPES
from src.services.loan_repository import (
    get_all_loans_including_completed,
    extend_loan_maturity,
    update_loan_info,
)
from src.utils.helpers import format_currency


def render_loan_edit_form():
    """대출 수정 / 만기 연장 화면"""
    
    st.title("🔄 대출 수정 / 만기 연장")
    st.caption("기존 대출의 만기 연장, 금리 변경, 정보 수정을 처리합니다.")
    
    # 모든 대출 가져오기
    all_loans = get_all_loans_including_completed()
    
    if not all_loans:
        st.warning("⚠️ 등록된 대출이 없습니다.")
        return
    
    # 대출 선택
    st.divider()
    
    loan_options = {}
    for loan in all_loans:
        status_emoji = "🟢" if loan.status == "진행중" else ("✅" if loan.status == "완납" else "🔄")
        rate_emoji = "🔴" if loan.interest_rate >= 5 else ("🟡" if loan.interest_rate >= 4 else "🟢")
        label = f"{status_emoji} {rate_emoji} {loan.loan_name} ({loan.interest_rate}%, {format_currency(loan.current_balance)})"
        loan_options[label] = loan.loan_id
    
    selected_label = st.selectbox(
        "🔍 수정할 대출 선택",
        options=list(loan_options.keys()),
        index=0
    )
    selected_loan_id = loan_options[selected_label]
    selected_loan = next((l for l in all_loans if l.loan_id == selected_loan_id), None)
    
    if not selected_loan:
        st.error("❌ 대출을 찾을 수 없습니다.")
        return
    
    st.divider()
    
    # =========================================
    # 현재 정보 표시
    # =========================================
    st.markdown("### 📋 현재 대출 정보")
    
    info_col1, info_col2, info_col3, info_col4 = st.columns(4)
    
    with info_col1:
        st.metric(
            label="현재 잔액",
            value=format_currency(selected_loan.current_balance)
        )
    
    with info_col2:
        st.metric(
            label="금리",
            value=f"{selected_loan.interest_rate}%",
            help=f"{selected_loan.rate_type}"
        )
    
    with info_col3:
        st.metric(
            label="만기일",
            value=selected_loan.maturity_date
        )
    
    with info_col4:
        try:
            maturity = datetime.strptime(selected_loan.maturity_date, "%Y-%m-%d").date()
            today = date.today()
            days_left = (maturity - today).days
            
            if days_left < 0:
                st.metric(label="만기까지", value="지남", delta="만기 도래")
            elif days_left < 30:
                st.metric(label="만기까지", value=f"{days_left}일", delta="⚠️ 임박")
            elif days_left < 365:
                st.metric(label="만기까지", value=f"{days_left}일")
            else:
                years = days_left / 365
                st.metric(label="만기까지", value=f"약 {years:.1f}년")
        except:
            st.metric(label="만기까지", value="-")
    
    # 추가 정보
    st.caption(
        f"🏦 {selected_loan.bank_name} ({selected_loan.branch}) | "
        f"💼 {selected_loan.repayment_method} | "
        f"📅 매월 {selected_loan.payment_day}일 자동이체 | "
        f"🔢 {selected_loan.account_number}"
    )
    
    st.divider()
    
    # =========================================
    # 작업 선택
    # =========================================
    st.markdown("### 🔧 어떤 변경을 하시겠어요?")
    
    operation = st.radio(
        "작업 종류",
        options=[
            "🔄 만기 연장 (만기일 + 금리 변경)",
            "💯 금리만 변경",
            "📝 기타 정보 수정",
        ],
        label_visibility="collapsed"
    )
    
    st.divider()
    
    # =========================================
    # 만기 연장 폼 (체크박스를 폼 밖으로 빼서 즉시 반영)
    # =========================================
    if operation == "🔄 만기 연장 (만기일 + 금리 변경)":
        st.markdown("### 🔄 만기 연장")
        st.caption("만기일을 연장하고, 필요하면 금리도 함께 변경합니다.")
        
        # 새 만기일 (폼 밖)
        try:
            current_maturity = datetime.strptime(selected_loan.maturity_date, "%Y-%m-%d").date()
            default_new_maturity = date(
                current_maturity.year + 1,
                current_maturity.month,
                current_maturity.day
            )
        except (ValueError, OSError):
            default_new_maturity = date(date.today().year + 1, date.today().month, 28)
        
        new_maturity_date = st.date_input(
            "📅 새 만기일 *",
            value=default_new_maturity,
            min_value=date.today(),
            help="기본값: 기존 만기일에서 1년 연장",
            key="new_maturity_date"
        )
        
        # 연장 기간 계산
        try:
            old_maturity = datetime.strptime(selected_loan.maturity_date, "%Y-%m-%d").date()
            ext_days = (new_maturity_date - old_maturity).days
            ext_years = ext_days / 365
            if ext_days > 0:
                st.success(f"✅ 연장 기간: 약 **{ext_years:.1f}년** ({ext_days}일)")
            else:
                st.warning("⚠️ 새 만기일이 기존 만기일보다 빠르거나 같습니다.")
        except:
            pass
        
        st.markdown("#### 💯 금리 변경 (선택사항)")
        st.caption("만기 연장 시 은행이 금리를 변경할 수 있습니다. 변경된 경우만 체크하세요.")
        
        # 체크박스 (폼 밖!) - 즉시 반영됨
        change_rate = st.checkbox(
            "✅ 금리도 함께 변경",
            value=False,
            help="체크하면 새 금리 입력 칸이 나타납니다.",
            key="change_rate_checkbox"
        )
        
        # 체크박스 결과에 따라 즉시 화면 변경
        new_rate = None
        new_rate_type = None
        new_rate_spread = None
        
        if change_rate:
            with st.container(border=True):
                st.markdown("##### 💰 새 금리 정보 입력")
                
                col_rate1, col_rate2 = st.columns(2)
                
                with col_rate1:
                    new_rate = st.number_input(
                        f"새 금리 (%) - 현재: {selected_loan.interest_rate}%",
                        min_value=0.0,
                        max_value=30.0,
                        value=float(selected_loan.interest_rate),
                        step=0.01,
                        format="%.2f",
                        help="우리은행 새 약정서 기준 금리 입력",
                        key="new_rate_input"
                    )
                    
                    new_rate_type = st.selectbox(
                        f"금리 종류 - 현재: {selected_loan.rate_type}",
                        options=RATE_TYPES,
                        index=RATE_TYPES.index(selected_loan.rate_type) if selected_loan.rate_type in RATE_TYPES else 0,
                        key="new_rate_type_select"
                    )
                
                with col_rate2:
                    new_rate_spread = st.number_input(
                        f"새 가산금리 (%) - 현재: {selected_loan.rate_spread}%",
                        min_value=0.0,
                        max_value=10.0,
                        value=float(selected_loan.rate_spread),
                        step=0.01,
                        format="%.2f",
                        key="new_rate_spread_input"
                    )
                    
                    if new_rate_type == "변동":
                        st.caption(f"📊 기준금리: {selected_loan.rate_base or '미입력'}")
                
                # 변경사항 미리보기
                if new_rate != selected_loan.interest_rate:
                    diff = new_rate - selected_loan.interest_rate
                    if diff > 0:
                        st.warning(f"📈 금리 인상: {selected_loan.interest_rate}% → {new_rate}% (+{diff:.2f}%p)")
                    else:
                        st.success(f"📉 금리 인하: {selected_loan.interest_rate}% → {new_rate}% ({diff:.2f}%p)")
        
        st.divider()
        
        # 폼 (제출 부분)
        with st.form("extend_form", clear_on_submit=False):
            st.markdown("#### 📝 변경 정보")
            
            reason = st.text_input(
                "변경 사유",
                value="만기 1년 연장",
                placeholder="예: 만기 1년 연장, 자금 사정상 연장"
            )
            
            memo = st.text_area(
                "메모 (선택)",
                placeholder="예: 우리은행과 협의 완료, 기존 조건 유지",
                max_chars=300
            )
            
            changed_by = st.selectbox(
                "👤 처리자",
                options=["대표님", "남편"]
            )
            
            # 변경 사항 요약
            st.markdown("#### 📋 변경 사항 요약")
            
            summary = [f"📅 만기일: {selected_loan.maturity_date} → **{new_maturity_date}**"]
            
            if change_rate:
                if new_rate is not None and new_rate != selected_loan.interest_rate:
                    summary.append(f"💯 금리: {selected_loan.interest_rate}% → **{new_rate}%**")
                if new_rate_type is not None and new_rate_type != selected_loan.rate_type:
                    summary.append(f"📊 금리 종류: {selected_loan.rate_type} → **{new_rate_type}**")
                if new_rate_spread is not None and new_rate_spread != selected_loan.rate_spread:
                    summary.append(f"➕ 가산금리: {selected_loan.rate_spread}% → **{new_rate_spread}%**")
            
            for item in summary:
                st.markdown(f"- {item}")
            
            # 제출
            submitted = st.form_submit_button(
                "💾 만기 연장 확정",
                type="primary",
                use_container_width=True
            )
            
            if submitted:
                with st.spinner("저장 중..."):
                    result = extend_loan_maturity(
                        loan_id=selected_loan_id,
                        new_maturity_date=str(new_maturity_date),
                        new_interest_rate=new_rate if change_rate else None,
                        new_rate_type=new_rate_type if change_rate else None,
                        new_rate_spread=new_rate_spread if change_rate else None,
                        reason=reason,
                        memo=memo,
                        changed_by=changed_by,
                    )
                
                if result['success']:
                    st.success(result['message'])
                    st.balloons()
                    
                    # 다음 단계 안내
                    st.info(
                        "💡 **다음 단계**\n"
                        "- 대시보드에서 갱신된 정보를 확인하세요.\n"
                        "- 우리은행에서도 새 약정서를 받으셨는지 확인하세요.\n"
                        "- 시뮬레이터에서도 새 만기 기준으로 자동 계산됩니다."
                    )
                else:
                    st.error(result['message'])
    
    # =========================================
    # 금리만 변경 폼
    # =========================================
    elif operation == "💯 금리만 변경":
        st.markdown("### 💯 금리 변경")
        st.caption("변동금리 변경, 우대금리 적용 등 금리만 수정합니다.")
        
        with st.form("rate_change_form", clear_on_submit=False):
            col1, col2 = st.columns(2)
            
            with col1:
                new_rate = st.number_input(
                    f"새 금리 (%) (현재: {selected_loan.interest_rate}%)",
                    min_value=0.0,
                    max_value=30.0,
                    value=float(selected_loan.interest_rate),
                    step=0.01,
                    format="%.2f"
                )
                
                new_rate_type = st.selectbox(
                    f"금리 종류 (현재: {selected_loan.rate_type})",
                    options=RATE_TYPES,
                    index=RATE_TYPES.index(selected_loan.rate_type) if selected_loan.rate_type in RATE_TYPES else 0
                )
            
            with col2:
                new_rate_spread = st.number_input(
                    f"가산금리 (%) (현재: {selected_loan.rate_spread}%)",
                    min_value=0.0,
                    max_value=10.0,
                    value=float(selected_loan.rate_spread),
                    step=0.01,
                    format="%.2f"
                )
                
                new_rate_base = st.text_input(
                    f"기준금리 (현재: {selected_loan.rate_base or '미입력'})",
                    value=selected_loan.rate_base or "",
                    placeholder="예: KORIBOR 3개월"
                )
            
            reason = st.text_input(
                "변경 사유",
                placeholder="예: 변동금리 인상 반영, 우대금리 적용"
            )
            
            memo = st.text_area(
                "메모",
                placeholder="우리은행 통보 일자 등",
                max_chars=300
            )
            
            changed_by = st.selectbox(
                "👤 처리자",
                options=["대표님", "남편"]
            )
            
            submitted = st.form_submit_button(
                "💾 금리 변경 확정",
                type="primary",
                use_container_width=True
            )
            
            if submitted:
                updates = {}
                if new_rate != selected_loan.interest_rate:
                    updates['interest_rate'] = new_rate
                if new_rate_type != selected_loan.rate_type:
                    updates['rate_type'] = new_rate_type
                if new_rate_spread != selected_loan.rate_spread:
                    updates['rate_spread'] = new_rate_spread
                if new_rate_base != selected_loan.rate_base:
                    updates['rate_base'] = new_rate_base
                
                if not updates:
                    st.warning("⚠️ 변경 사항이 없습니다.")
                else:
                    with st.spinner("저장 중..."):
                        result = update_loan_info(
                            loan_id=selected_loan_id,
                            updates=updates,
                            reason=reason,
                            memo=memo,
                            changed_by=changed_by,
                        )
                    
                    if result['success']:
                        st.success(result['message'])
                        st.balloons()
                    else:
                        st.error(result['message'])
    
    # =========================================
    # 기타 정보 수정 폼
    # =========================================
    elif operation == "📝 기타 정보 수정":
        st.markdown("### 📝 기타 정보 수정")
        st.caption("대출명, 지점, 메모, 잔액 등 기타 정보를 수정합니다.")
        
        st.warning("⚠️ **잔액 수정은 신중하게!** 부분상환/정기상환을 통한 자동 갱신이 정상입니다. 직접 수정은 데이터 보정용으로만 사용하세요.")
        
        with st.form("info_edit_form", clear_on_submit=False):
            col1, col2 = st.columns(2)
            
            with col1:
                new_loan_name = st.text_input(
                    "대출명",
                    value=selected_loan.loan_name
                )
                
                new_bank = st.text_input(
                    "은행명",
                    value=selected_loan.bank_name
                )
                
                new_branch = st.text_input(
                    "지점명",
                    value=selected_loan.branch or ""
                )
                
                new_account = st.text_input(
                    "계좌번호",
                    value=selected_loan.account_number
                )
            
            with col2:
                new_payment_day = st.number_input(
                    "이체일",
                    min_value=1,
                    max_value=31,
                    value=selected_loan.payment_day
                )
                
                # 잔액 직접 수정 (드물게)
                edit_balance = st.checkbox(
                    "잔액 직접 수정 (보정용)",
                    value=False
                )
                
                if edit_balance:
                    new_balance = st.number_input(
                        "현재 잔액 (원)",
                        min_value=0.0,
                        max_value=float(selected_loan.initial_amount),
                        value=float(selected_loan.current_balance),
                        step=10000.0
                    )
                else:
                    new_balance = None
            
            new_memo = st.text_area(
                "메모",
                value=selected_loan.memo or "",
                max_chars=500,
                height=100
            )
            
            reason = st.text_input(
                "변경 사유",
                placeholder="예: 정보 정정, 잔액 보정"
            )
            
            changed_by = st.selectbox(
                "👤 처리자",
                options=["대표님", "남편"]
            )
            
            submitted = st.form_submit_button(
                "💾 정보 수정 확정",
                type="primary",
                use_container_width=True
            )
            
            if submitted:
                updates = {}
                if new_loan_name != selected_loan.loan_name:
                    updates['loan_name'] = new_loan_name
                if new_bank != selected_loan.bank_name:
                    updates['bank_name'] = new_bank
                if new_branch != selected_loan.branch:
                    updates['branch'] = new_branch
                if new_account != selected_loan.account_number:
                    updates['account_number'] = new_account
                if new_payment_day != selected_loan.payment_day:
                    updates['payment_day'] = new_payment_day
                if new_memo != (selected_loan.memo or ""):
                    updates['memo'] = new_memo
                if edit_balance and new_balance is not None and new_balance != selected_loan.current_balance:
                    updates['current_balance'] = new_balance
                
                if not updates:
                    st.warning("⚠️ 변경 사항이 없습니다.")
                else:
                    with st.spinner("저장 중..."):
                        result = update_loan_info(
                            loan_id=selected_loan_id,
                            updates=updates,
                            reason=reason,
                            changed_by=changed_by,
                        )
                    
                    if result['success']:
                        st.success(result['message'])
                        st.balloons()
                    else:
                        st.error(result['message'])
    
    # =========================================
    # 변경 이력 표시
    # =========================================
    st.divider()
    
    with st.expander(f"📜 {selected_loan.loan_name} 변경 이력", expanded=False):
        recent = selected_loan.get_recent_changes(limit=10)
        
        if not recent:
            st.caption("아직 변경 이력이 없습니다.")
        else:
            st.caption(f"총 {len(selected_loan.change_logs)}건의 변경 이력 (최근 10건)")
            
            for log in recent:
                col_l1, col_l2, col_l3 = st.columns([2, 3, 4])
                
                with col_l1:
                    st.markdown(f"**{log.get('change_date', 'N/A')}**")
                    st.caption(log.get('change_type', 'N/A'))
                
                with col_l2:
                    if log.get('field_changed'):
                        st.caption(f"📝 {log.get('field_changed')}")
                        if log.get('old_value'):
                            st.caption(f"이전: {log.get('old_value')}")
                        if log.get('new_value'):
                            st.caption(f"변경: {log.get('new_value')}")
                
                with col_l3:
                    if log.get('reason'):
                        st.caption(f"💬 {log.get('reason')}")
                    if log.get('changed_by'):
                        st.caption(f"👤 {log.get('changed_by')}")


if __name__ == "__main__":
    render_loan_edit_form()