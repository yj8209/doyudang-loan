"""
YJ&HK 대출관리 앱 - 메인
"""

import streamlit as st
from src.services.loan_repository import get_active_loans
from src.utils.helpers import format_currency


# 페이지 설정
st.set_page_config(
    page_title="YJ&HK 대출관리",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 커스텀 CSS
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 0.5rem;
    }
    .metric-label {
        font-size: 0.875rem;
        color: #555;
        margin-bottom: 0.25rem;
    }
    .metric-value {
        font-size: 1.25rem;
        font-weight: bold;
        color: #262730;
    }
</style>
""", unsafe_allow_html=True)


def render_metric(label, value, suffix=""):
    """깔끔한 메트릭 표시"""
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}{suffix}</div>
    </div>
    """, unsafe_allow_html=True)


def render_dashboard():
    """메인 대시보드"""
    
    st.title("💰 YJ&HK 대출관리")
    st.caption("5년 안에 대출을 갚아나가는 우리 부부의 여정")
    
    with st.spinner("데이터 불러오는 중..."):
        try:
            loans = get_active_loans()
        except Exception as e:
            st.error(f"❌ 데이터 로드 실패: {e}")
            return
    
    if not loans:
        st.warning("⚠️ 등록된 대출이 없습니다.")
        return
    
    # 통계 계산
    total_balance = sum(loan.current_balance for loan in loans)
    total_initial = sum(loan.initial_amount for loan in loans)
    total_repaid = total_initial - total_balance
    overall_progress = (total_repaid / total_initial * 100) if total_initial > 0 else 0
    
    # 5년 목표
    target_balance = 19820000
    target_progress = ((total_initial - target_balance) / total_initial * 100) if total_initial > 0 else 0
    remaining_to_target = total_balance - target_balance
    
    # 상단 요약
    col1, col2 = st.columns(2)
    
    with col1:
        render_metric("💰 총 대출 잔액", format_currency(total_balance))
        render_metric("📊 누적 상환액", format_currency(total_repaid))
    
    with col2:
        render_metric("📋 대출 건수", f"{len(loans)}건")
        render_metric("📈 전체 상환율", f"{overall_progress:.1f}%")
    
    st.markdown(f"**전체 진행률: {overall_progress:.1f}%**")
    st.progress(overall_progress / 100)
    
    st.divider()
    st.subheader("🎯 5년 목표")
    
    goal_col1, goal_col2, goal_col3 = st.columns(3)
    with goal_col1:
        render_metric("목표 잔액 (2031.04)", format_currency(target_balance))
    with goal_col2:
        render_metric("목표까지 갚아야 할 금액", format_currency(remaining_to_target))
    with goal_col3:
        render_metric("목표 상환률", f"{target_progress:.1f}%")
    
    st.divider()
    
    # 대출별 카드
    st.subheader("📋 대출 현황 (이자율 높은 순)")
    st.caption("이자율이 높은 대출부터 우선 상환하면 이자 절감 효과가 가장 큽니다.")
    
    medals = ["🥇", "🥈", "🥉"]
    
    for i, loan in enumerate(loans):
        medal = medals[i] if i < 3 else f"{i+1}."
        
        with st.container():
            header_col1, header_col2 = st.columns([4, 1])
            with header_col1:
                st.markdown(f"### {medal} {loan.loan_name}")
            with header_col2:
                rate_emoji = "🔴" if loan.interest_rate >= 5 else ("🟡" if loan.interest_rate >= 4 else "🟢")
                st.markdown(f"### {rate_emoji} {loan.interest_rate}%")
                st.caption(f"{loan.rate_type}금리")
            
            info_col1, info_col2, info_col3, info_col4 = st.columns(4)
            
            with info_col1:
                st.markdown("**잔액**")
                st.markdown(f"#### {format_currency(loan.current_balance)}")
            
            with info_col2:
                st.markdown("**최초 금액**")
                st.markdown(f"#### {format_currency(loan.initial_amount)}")
            
            with info_col3:
                st.markdown("**상환방식**")
                st.markdown(f"#### {loan.repayment_method}")
            
            with info_col4:
                progress = loan.get_progress_percent()
                st.markdown("**상환률**")
                st.markdown(f"#### {progress:.1f}%")
            
            st.progress(progress / 100)
            
            st.caption(
                f"🏦 {loan.bank_name} ({loan.branch}) | "
                f"📅 매월 {loan.payment_day}일 이체 | "
                f"⏰ 만기: {loan.maturity_date}"
            )
            
            if loan.memo:
                st.info(f"💬 {loan.memo}")
        
        st.divider()
    
    # 데이터 정보
    with st.expander("📊 데이터 정보"):
        st.markdown(f"""
        - **데이터 위치**: Google Drive `두유당_대출관리/`
        - **5년 목표**: 잔액 {format_currency(target_balance)} (94.8% 상환)
        - **이자 절감 예상**: 약 2,100만원
        """)


# ============= 메인 =============
def main():
    """메인 함수: 사이드바로 페이지 전환"""
    
    # 사이드바 메뉴
    with st.sidebar:
        st.title("💰 YJ&HK 대출관리")
        st.divider()
        
        page = st.radio(
            "메뉴",
            ["🏠 대시보드", "💸 부분 상환 입력", "📋 정기상환 확정", "🎯 부분상환 시뮬레이터", "🆕 신규 대출 추가", "🔄 대출 수정 / 만기 연장"],
            label_visibility="collapsed"
        )
        
        st.divider()
        
        st.markdown("### 🚀 곧 추가될 기능")
        st.caption("""
        - 📈 5년 진행 그래프
        - 📅 캘린더 뷰
        - 🎁 이벤트 자금 관리
        """)
        
        st.divider()
        st.caption("💡 부부의 자산을 함께 관리하는 도구")
    
    # 페이지 라우팅
    if page == "🏠 대시보드":
        render_dashboard()
    elif page == "💸 부분 상환 입력":
        from src.views.payment_form import render_payment_form
        render_payment_form()
    elif page == "📋 정기상환 확정":
        from src.views.regular_payment_form import render_regular_payment_form
        render_regular_payment_form()
    elif page == "🎯 부분상환 시뮬레이터":
        from src.views.simulator_view import render_simulator
        render_simulator()
    elif page == "🆕 신규 대출 추가":
        from src.views.new_loan_form import render_new_loan_form
        render_new_loan_form()
    elif page == "🔄 대출 수정 / 만기 연장":
        from src.views.loan_edit_form import render_loan_edit_form
        render_loan_edit_form()      


if __name__ == "__main__":
    main()