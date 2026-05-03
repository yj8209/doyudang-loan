"""
두유당 대출관리 앱 - 메인 화면
"""

import streamlit as st
from src.services.loan_repository import get_active_loans
from src.utils.helpers import format_currency


# 페이지 설정
st.set_page_config(
    page_title="두유당 대출관리",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)


def main():
    """메인 대시보드"""
    
    # 헤더
    st.title("💰 두유당 대출관리")
    st.caption("5년 안에 대출을 갚아나가는 우리 부부의 여정")
    
    # 데이터 로드
    with st.spinner("데이터 불러오는 중..."):
        try:
            loans = get_active_loans()
        except Exception as e:
            st.error(f"❌ 데이터 로드 실패: {e}")
            st.info("💡 .env 파일과 인증 토큰을 확인해주세요.")
            return
    
    if not loans:
        st.warning("⚠️ 등록된 대출이 없습니다.")
        st.info("좌측 메뉴에서 [대출 추가]를 통해 대출을 등록해주세요.")
        return
    
    # 총 잔액 계산
    total_balance = sum(loan.current_balance for loan in loans)
    total_initial = sum(loan.initial_amount for loan in loans)
    total_repaid = total_initial - total_balance
    overall_progress = (total_repaid / total_initial * 100) if total_initial > 0 else 0
    
    # 상단 요약 카드
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="총 대출 잔액",
            value=format_currency(total_balance),
        )
    
    with col2:
        st.metric(
            label="총 대출 건수",
            value=f"{len(loans)}건",
        )
    
    with col3:
        st.metric(
            label="누적 상환액",
            value=format_currency(total_repaid),
        )
    
    with col4:
        st.metric(
            label="전체 상환율",
            value=f"{overall_progress:.1f}%",
        )
    
    # 진행률 바
    st.progress(overall_progress / 100)
    
    st.divider()
    
    # 대출별 카드 (이자율 높은 순)
    st.subheader("📋 대출 현황 (이자율 높은 순)")
    st.caption("이자율이 높은 대출부터 우선 상환하면 이자 절감 효과가 가장 큽니다.")
    
    medals = ["🥇", "🥈", "🥉"]
    
    for i, loan in enumerate(loans):
        medal = medals[i] if i < 3 else f"{i+1}."
        
        with st.container():
            # 대출별 카드
            card_col1, card_col2 = st.columns([3, 1])
            
            with card_col1:
                # 대출 이름 + 메달
                st.markdown(f"### {medal} {loan.loan_name}")
                
                # 정보 라인
                info_col1, info_col2, info_col3, info_col4 = st.columns(4)
                
                with info_col1:
                    st.markdown("**잔액**")
                    st.markdown(f"### {format_currency(loan.current_balance)}")
                
                with info_col2:
                    st.markdown("**금리**")
                    rate_emoji = "🔴" if loan.interest_rate >= 5 else ("🟡" if loan.interest_rate >= 4 else "🟢")
                    st.markdown(f"### {rate_emoji} {loan.interest_rate}%")
                    st.caption(f"{loan.rate_type}")
                
                with info_col3:
                    st.markdown("**상환방식**")
                    st.markdown(f"### {loan.repayment_method}")
                
                with info_col4:
                    progress = loan.get_progress_percent()
                    st.markdown("**상환률**")
                    st.markdown(f"### {progress:.1f}%")
                
                # 진행률 바
                st.progress(progress / 100)
                
                # 추가 정보
                st.caption(
                    f"🏦 {loan.bank_name} ({loan.branch}) | "
                    f"📅 매월 {loan.payment_day}일 이체 | "
                    f"⏰ 만기: {loan.maturity_date}"
                )
                
                if loan.memo:
                    st.info(f"💬 {loan.memo}")
            
            with card_col2:
                st.markdown("**액션**")
                st.button(f"➕ 부분 상환", key=f"repay_{loan.loan_id}", disabled=True, help="다음 단계에서 구현 예정")
                st.button(f"📋 상세보기", key=f"detail_{loan.loan_id}", disabled=True, help="다음 단계에서 구현 예정")
        
        st.divider()
    
    # 하단 정보
    with st.expander("📊 데이터 정보"):
        st.markdown(f"""
        - **데이터 위치**: Google Drive `두유당_대출관리/loans.json`
        - **마지막 업데이트**: {loans[0].updated_at if loans else '없음'}
        - **5년 목표**: 잔액 1,982만원 (94.8% 상환)
        """)


if __name__ == "__main__":
    main()