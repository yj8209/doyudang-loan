"""
이벤트 자금 관리 화면 (Streamlit)
- 향후 5년 자금 계획 등록/관리
- 보너스, 적금 만기, 주식 매도 등
- 시뮬레이터와 연계
"""

import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
from src.models.event import FundEvent, EVENT_TYPES, USE_PRIORITY
from src.services.event_repository import (
    get_all_events,
    get_upcoming_events,
    get_received_events,
    add_event,
    update_event,
    delete_event,
    mark_as_received,
    get_total_upcoming_amount,
)
from src.services.loan_repository import get_active_loans
from src.utils.helpers import format_currency


def render_event_view():
    """이벤트 자금 관리 화면"""
    
    st.title("🎁 이벤트 자금 관리")
    st.caption("향후 5년 동안 발생할 자금 이벤트(보너스, 적금 만기 등)를 등록하고 관리합니다.")
    
    # 모든 이벤트
    all_events = get_all_events()
    upcoming = get_upcoming_events(months_ahead=60)
    received = get_received_events()
    
    # =========================================
    # 요약 통계
    # =========================================
    st.divider()
    st.markdown("### 📊 요약")
    
    summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)
    
    total_upcoming = sum(e.amount for e in upcoming)
    total_received = sum(e.actual_amount for e in received)
    
    # 이번 달 예정 이벤트
    today = date.today()
    this_month = [
        e for e in upcoming
        if e.expected_date.startswith(today.strftime("%Y-%m"))
    ]
    
    with summary_col1:
        st.metric(
            label="📅 등록된 이벤트",
            value=f"{len(all_events)}건"
        )
    
    with summary_col2:
        st.metric(
            label="💰 향후 예상 자금",
            value=format_currency(total_upcoming),
            help="향후 5년 이내 예상 수령액"
        )
    
    with summary_col3:
        st.metric(
            label="✅ 수령 완료",
            value=format_currency(total_received)
        )
    
    with summary_col4:
        st.metric(
            label="🔵 이번 달 예정",
            value=f"{len(this_month)}건"
        )
    
    # 시뮬레이터 연계 안내
    if total_upcoming > 0:
        st.info(
            f"💡 **향후 자금으로 부분상환 시뮬레이션**\n\n"
            f"향후 5년 동안 약 **{format_currency(total_upcoming)}**의 자금이 들어올 예정입니다.\n"
            f"이 자금으로 어디 갚는 게 효과적일지 시뮬레이터에서 확인해보세요.\n\n"
            f"**부분상환 시뮬레이터 → 가용 자금 입력**: `{int(total_upcoming)}`"
        )
    
    st.divider()
    
    # =========================================
    # 새 이벤트 등록
    # =========================================
    with st.expander("➕ 새 이벤트 등록", expanded=(len(all_events) == 0)):
        with st.form("new_event_form", clear_on_submit=True):
            
            col1, col2 = st.columns(2)
            
            with col1:
                event_name = st.text_input(
                    "이벤트 이름 *",
                    placeholder="예: 5월 보너스, 11월 적금 만기"
                )
                
                event_type = st.selectbox(
                    "이벤트 종류 *",
                    options=EVENT_TYPES,
                    index=0
                )
                
                amount = st.number_input(
                    "예상 금액 (원) *",
                    min_value=0,
                    value=5000000,
                    step=100000
                )
            
            with col2:
                expected_date_input = st.date_input(
                    "예상 날짜 *",
                    value=date.today() + timedelta(days=30),
                    min_value=date.today() - timedelta(days=365),
                    max_value=date(today.year + 5, 12, 31),
                    help="이벤트가 발생할 예상 날짜"
                )
                
                use_priority = st.selectbox(
                    "사용 계획",
                    options=USE_PRIORITY,
                    index=0,  # 기본: 부분상환
                    help="이 자금을 어디에 사용할 계획인지"
                )
                
                created_by = st.selectbox(
                    "등록자",
                    options=["대표님", "남편"]
                )
            
            memo = st.text_area(
                "메모 (선택)",
                placeholder="예: 분기별 정기 보너스, 만기 후 자동이체 해지 필요",
                max_chars=300
            )
            
            submitted = st.form_submit_button(
                "💾 이벤트 등록",
                type="primary",
                use_container_width=True
            )
            
            if submitted:
                if not event_name.strip():
                    st.error("❌ 이벤트 이름을 입력해주세요.")
                elif amount <= 0:
                    st.error("❌ 금액은 0보다 커야 합니다.")
                else:
                    new_event = FundEvent(
                        event_name=event_name.strip(),
                        event_type=event_type,
                        amount=float(amount),
                        expected_date=str(expected_date_input),
                        use_priority=use_priority,
                        memo=memo.strip(),
                        created_by=created_by,
                    )
                    
                    with st.spinner("저장 중..."):
                        result = add_event(new_event)
                    
                    if result['success']:
                        st.success(result['message'])
                        st.balloons()
                        st.info("💡 페이지를 새로고침하면 등록된 이벤트가 표시됩니다.")
                    else:
                        st.error(result['message'])
    
    st.divider()
    
    # =========================================
    # 향후 이벤트 목록
    # =========================================
    if upcoming:
        st.markdown(f"### 📅 향후 이벤트 ({len(upcoming)}건)")
        
        for event in upcoming:
            # 카드별 컨테이너
            with st.container(border=True):
                # 헤더
                header_col1, header_col2, header_col3 = st.columns([2, 2, 1])
                
                with header_col1:
                    st.markdown(f"### 💰 {event.event_name}")
                    st.caption(f"📌 {event.event_type}")
                
                with header_col2:
                    st.markdown(f"**예상일**: {event.expected_date}")
                    st.caption(event.get_status())
                
                with header_col3:
                    action = st.selectbox(
                        "액션",
                        options=["선택", "✅ 수령 처리", "📝 수정", "🗑 삭제"],
                        key=f"action_{event.event_id}",
                        label_visibility="collapsed"
                    )
                
                # 정보
                info_col1, info_col2, info_col3 = st.columns(3)
                
                with info_col1:
                    st.metric(
                        label="💵 예상 금액",
                        value=format_currency(event.amount)
                    )
                
                with info_col2:
                    st.markdown(f"**🎯 사용 계획**\n\n{event.use_priority}")
                
                with info_col3:
                    st.markdown(f"**👤 등록자**\n\n{event.created_by or '미입력'}")
                
                if event.memo:
                    st.caption(f"📝 {event.memo}")
                
                # 액션 처리
                if action == "✅ 수령 처리":
                    with st.form(f"receive_form_{event.event_id}"):
                        st.markdown("##### ✅ 수령 처리")
                        
                        col_r1, col_r2 = st.columns(2)
                        
                        with col_r1:
                            actual_date = st.date_input(
                                "실제 수령일",
                                value=date.today(),
                                max_value=date.today(),
                                key=f"date_{event.event_id}"
                            )
                        
                        with col_r2:
                            actual_amount = st.number_input(
                                "실제 수령액",
                                min_value=0,
                                value=int(event.amount),
                                step=10000,
                                key=f"amount_{event.event_id}"
                            )
                        
                        receive_submitted = st.form_submit_button(
                            "✅ 수령 완료 처리",
                            type="primary",
                            use_container_width=True
                        )
                        
                        if receive_submitted:
                            with st.spinner("처리 중..."):
                                result = mark_as_received(
                                    event_id=event.event_id,
                                    actual_amount=float(actual_amount),
                                    actual_date=str(actual_date)
                                )
                            
                            if result['success']:
                                st.success(result['message'])
                                st.balloons()
                                
                                # 시뮬레이터 안내
                                st.info(
                                    f"💡 **다음 단계**\n\n"
                                    f"수령한 {format_currency(actual_amount)}로 어디 갚을지 시뮬레이터에서 확인하세요!\n\n"
                                    f"사이드바 → 🎯 부분상환 시뮬레이터 → 가용 자금: {int(actual_amount)}"
                                )
                            else:
                                st.error(result['message'])
                
                elif action == "📝 수정":
                    with st.form(f"edit_form_{event.event_id}"):
                        st.markdown("##### 📝 이벤트 수정")
                        
                        col_e1, col_e2 = st.columns(2)
                        
                        with col_e1:
                            new_name = st.text_input(
                                "이벤트 이름",
                                value=event.event_name,
                                key=f"name_{event.event_id}"
                            )
                            
                            new_amount = st.number_input(
                                "예상 금액",
                                min_value=0,
                                value=int(event.amount),
                                step=100000,
                                key=f"new_amount_{event.event_id}"
                            )
                        
                        with col_e2:
                            try:
                                current_date = datetime.strptime(event.expected_date, "%Y-%m-%d").date()
                            except:
                                current_date = date.today()
                            
                            new_date = st.date_input(
                                "예상 날짜",
                                value=current_date,
                                key=f"new_date_{event.event_id}"
                            )
                            
                            new_priority = st.selectbox(
                                "사용 계획",
                                options=USE_PRIORITY,
                                index=USE_PRIORITY.index(event.use_priority) if event.use_priority in USE_PRIORITY else 0,
                                key=f"priority_{event.event_id}"
                            )
                        
                        new_memo = st.text_area(
                            "메모",
                            value=event.memo,
                            max_chars=300,
                            key=f"memo_{event.event_id}"
                        )
                        
                        edit_submitted = st.form_submit_button(
                            "💾 수정 확정",
                            type="primary",
                            use_container_width=True
                        )
                        
                        if edit_submitted:
                            updates = {
                                'event_name': new_name,
                                'amount': float(new_amount),
                                'expected_date': str(new_date),
                                'use_priority': new_priority,
                                'memo': new_memo,
                            }
                            
                            with st.spinner("저장 중..."):
                                result = update_event(event.event_id, updates)
                            
                            if result['success']:
                                st.success(result['message'])
                            else:
                                st.error(result['message'])
                
                elif action == "🗑 삭제":
                    with st.form(f"delete_form_{event.event_id}"):
                        st.markdown("##### 🗑 이벤트 삭제")
                        st.warning(f"⚠️ '{event.event_name}'을 삭제하시겠습니까?")
                        
                        confirm = st.checkbox(
                            "확인했습니다.",
                            key=f"confirm_del_{event.event_id}"
                        )
                        
                        delete_submitted = st.form_submit_button(
                            "🗑 삭제 확정",
                            type="primary",
                            use_container_width=True
                        )
                        
                        if delete_submitted:
                            if not confirm:
                                st.error("❌ 확인 체크박스를 체크해주세요.")
                            else:
                                with st.spinner("삭제 중..."):
                                    result = delete_event(event.event_id)
                                
                                if result['success']:
                                    st.success(result['message'])
                                else:
                                    st.error(result['message'])
    else:
        st.info("ℹ️ 등록된 향후 이벤트가 없습니다. 위에서 새 이벤트를 등록해주세요.")
    
    # =========================================
    # 수령 완료 이벤트
    # =========================================
    if received:
        st.divider()
        with st.expander(f"✅ 수령 완료 이벤트 ({len(received)}건)"):
            for event in received:
                col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
                
                with col1:
                    st.markdown(f"**{event.event_name}**")
                    st.caption(event.event_type)
                
                with col2:
                    st.markdown(f"📅 {event.actual_date}")
                
                with col3:
                    st.markdown(f"💰 {format_currency(event.actual_amount)}")
                    if event.actual_amount != event.amount:
                        diff = event.actual_amount - event.amount
                        if diff > 0:
                            st.caption(f"📈 예상보다 {format_currency(abs(diff))} 많음")
                        else:
                            st.caption(f"📉 예상보다 {format_currency(abs(diff))} 적음")
                
                with col4:
                    if event.used_amount > 0:
                        st.caption(f"💸 사용: {format_currency(event.used_amount)}")
                    else:
                        st.caption(f"💼 미사용: {format_currency(event.actual_amount)}")
    
    # =========================================
    # 사용 가이드
    # =========================================
    st.divider()
    
    with st.expander("💡 이벤트 자금 관리 가이드"):
        st.markdown("""
        ### 활용 방법
        
        **1. 5년 자금 계획 수립**
        - 정기 보너스, 적금 만기 등 미리 등록
        - 향후 자금 흐름 한눈에 파악
        
        **2. 시뮬레이터 연계**
        - 등록된 자금으로 부분상환 시뮬레이션
        - "이 돈으로 어디 갚으면 효과적?" 자동 분석
        
        **3. 수령 후 처리**
        - 실제 수령 시 "✅ 수령 처리" 클릭
        - 실제 수령액 입력 (예상과 다를 수 있음)
        - 시뮬레이터로 즉시 분석 가능
        
        ### 사용 계획 종류
        
        - **부분상환**: 가장 추천! 이자율 높은 대출 우선
        - **비상금**: 6개월치 생활비 확보 후 추가 보유
        - **투자**: 다른 투자 기회 (주식, 부동산 등)
        - **지출**: 큰 지출 예정 (여행, 가전 등)
        - **미정**: 아직 결정 안 함
        
        ### 실생활 활용 예시
                    
        2026.05  남편 보너스 500만원  → 신용대출2 (5.58%) 부분상환
        2026.08  남편 보너스 500만원  → 신용대출1 (4.67%) 부분상환
        2026.11  적금 만기 620만원   → 신용대출2 만기상환
        2026.11  남편 보너스 500만원  → 주담대 부분상환 (장기 효과)
        2026.12  주식 매도 1500만원  → 신용대출1 완납 가능!
                    """)


if __name__ == "__main__":
    render_event_view()