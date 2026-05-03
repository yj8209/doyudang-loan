"""
두유당 대출관리 앱 - 메인 화면 (개선 버전)
"""

import streamlit as st
from src.services.loan_repository import get_active_loans
from src.utils.helpers import format_currency


st.set_page_config(
    page_title="두유당 대출관리",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 커스텀 CSS - 모바일/좁은 화면에서도 잘 보이게
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
    .loan-card {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 0.5rem;
        padding: 1.5rem;
        margin-bottom: 1rem;
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


def main():
    st.title("💰 두유당 대출관리")
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
    target_balance = 19820000  # 1,982만원
    target_progress = ((total_initial - target_balance) / total_initial * 100) if total_initial > 0 else 0
    remaining_to_target = total_balance - target_balance
    
    # 상단 요약 (커스텀 메트릭)
    col1, col2 = st.columns(2)
    
    with col1:
        render_metric("💰 총 대출 잔액", format_currency(total_balance))
        render_metric("📊 누적 상환액", format_currency(total_repaid))
    
    with col2:
        render_metric("📋 대출 건수", f"{len(loans)}건")
        render_metric("📈 전체 상환율", f"{overall_progress:.1f}%")
    
    st.markdown(f"**전체 진행률: {overall_progress:.1f}%**")
    st.progress(overall_progress / 100)
    
    # 5년 목표
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
            # 대출 헤더
            header_col1, header_col2 = st.columns([4, 1])
            with header_col1:
                st.markdown(f"### {medal} {loan.loan_name}")
            with header_col2:
                rate_emoji = "🔴" if loan.interest_rate >= 5 else ("🟡" if loan.interest_rate >= 4 else "🟢")
                st.markdown(f"### {rate_emoji} {loan.interest_rate}%")
                st.caption(f"{loan.rate_type}금리")
            
            # 대출 정보 4컬럼
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
            
            # 진행률 바
            st.progress(progress / 100)
            
            # 추가 정보 + 액션
            detail_col1, detail_col2 = st.columns([3, 1])
            with detail_col1:
                st.caption(
                    f"🏦 {loan.bank_name} ({loan.branch}) | "
                    f"📅 매월 {loan.payment_day}일 이체 | "
                    f"⏰ 만기: {loan.maturity_date}"
                )
                if loan.memo:
                    st.info(f"💬 {loan.memo}")
            
            with detail_col2:
                st.button(
                    "➕ 부분 상환",
                    key=f"repay_{loan.loan_id}",
                    disabled=True,
                    help="다음 단계에서 구현 예정",
                    use_container_width=True
                )
                st.button(
                    "📋 상세보기",
                    key=f"detail_{loan.loan_id}",
                    disabled=True,
                    help="다음 단계에서 구현 예정",
                    use_container_width=True
                )
        
        st.divider()
    
    # 하단 정보
    with st.expander("📊 데이터 정보"):
        st.markdown(f"""
        - **데이터 위치**: Google Drive `두유당_대출관리/loans.json`
        - **5년 목표**: 잔액 {format_currency(target_balance)} (94.8% 상환)
        - **이자 절감 예상**: 약 2,100만원
        """)
    
    # 사이드바
    with st.sidebar:
        st.header("🚀 다음 단계")
        st.markdown("""
        **곧 추가될 기능:**
        - ➕ 부분 상환 입력
        - 📋 정기상환 확정
        - 🎯 부분상환 시뮬레이터
        - 📈 5년 진행 그래프
        - 📅 캘린더 뷰
        - 🎁 이벤트 자금 관리
        """)
        
        st.divider()
        st.caption("💡 본 앱은 부부의 자산을 함께 관리하는 도구입니다.")


if __name__ == "__main__":
    main()
