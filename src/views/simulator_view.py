"""
부분상환 시뮬레이터 화면 (Streamlit)
- 가용 자금 입력 → 모든 대출별 효과 자동 계산
- 단기/장기/종합 추천
- 시각화 (차트, 비교 표)
"""

import streamlit as st
import pandas as pd
from src.services.loan_repository import get_active_loans
from src.services.simulator import (
    simulate_all_loans,
    get_recommendation,
    simulate_partial_payment,
)
from src.utils.helpers import format_currency


def render_simulator():
    """부분상환 시뮬레이터 화면"""
    
    st.title("🎯 부분상환 시뮬레이터")
    st.caption("가용 자금이 생겼을 때 어디에 갚는 게 가장 효율적인지 자동으로 분석해드립니다.")
    
    # 진행 중인 대출
    loans = get_active_loans()
    
    if not loans:
        st.warning("⚠️ 진행 중인 대출이 없습니다.")
        return
    
    # =========================================
    # 가용 자금 입력
    # =========================================
    st.divider()
    
    col_input1, col_input2 = st.columns([3, 1])
    
    with col_input1:
        st.markdown("### 💰 가용 자금 입력")
        amount = st.number_input(
            "부분상환할 수 있는 금액 (원)",
            min_value=0,
            max_value=int(sum(l.current_balance for l in loans)),
            value=1000000,
            step=100000,
            help="보너스, 적금 만기 등으로 사용 가능한 자금을 입력하세요.",
            label_visibility="collapsed"
        )
    
    with col_input2:
        st.markdown("**빠른 입력 예시**")
        st.caption("100만원 = 1000000")
        st.caption("500만원 = 5000000")
        st.caption("1000만원 = 10000000")
    
    if amount == 0:
        st.info("💡 위에 가용 자금을 입력하면 시뮬레이션이 시작됩니다.")
        return
    
    # =========================================
    # 시뮬레이션 실행
    # =========================================
    
    simulations = simulate_all_loans(loans, amount)
    recommendation = get_recommendation(simulations)
    
    if not recommendation:
        st.error("❌ 시뮬레이션을 실행할 수 없습니다.")
        return
    
    # =========================================
    # 추천 카드 (3개)
    # =========================================
    st.divider()
    st.markdown(f"### 📊 {format_currency(amount)} 부분상환 시 추천")
    
    rec_col1, rec_col2, rec_col3 = st.columns(3)
    
    # ⭐ 종합 추천
    with rec_col1:
        best = recommendation['best_overall']
        with st.container(border=True):
            st.markdown("### ⭐ 종합 추천")
            st.markdown(f"**{best['loan_name']}**")
            st.caption(f"이자율 {best['interest_rate']}% ({best['rate_type']})")
            
            st.metric(
                label="월 이자 절감",
                value=format_currency(best['monthly_savings'])
            )
            
            if best['months_until_maturity'] > 0:
                st.caption(f"📅 만기까지: {best['months_until_maturity']}개월")
            
            if best['is_paid_off']:
                st.success("🎉 완납 가능!")
            
            st.info(f"💡 {recommendation['reason']}")
    
    # 💸 단기 효과 최대
    with rec_col2:
        short = recommendation['best_short_term']
        with st.container(border=True):
            st.markdown("### 💸 단기 효과 최대")
            st.markdown(f"**{short['loan_name']}**")
            st.caption(f"이자율 {short['interest_rate']}%")
            
            st.metric(
                label="월 이자 절감",
                value=format_currency(short['monthly_savings']),
                help="당장 매월 줄어드는 이자"
            )
            
            st.caption(f"💰 즉시 효과 가장 큼")
    
    # 📈 장기 효과 최대
    with rec_col3:
        long = recommendation['best_long_term']
        with st.container(border=True):
            st.markdown("### 📈 장기 효과 최대")
            st.markdown(f"**{long['loan_name']}**")
            st.caption(f"이자율 {long['interest_rate']}%")
            
            st.metric(
                label="만기까지 총 절감",
                value=format_currency(long['total_savings']),
                help=f"만기까지 {long['months_until_maturity']}개월간 누적 절감"
            )
            
            st.caption(f"📈 장기 누적 효과 최대")
    
    # =========================================
    # 인사이트 박스
    # =========================================
    st.divider()
    st.markdown("### 💡 분석 인사이트")
    
    insight_col1, insight_col2 = st.columns(2)
    
    with insight_col1:
        # 단기 vs 장기 차이
        short_total = recommendation['best_short_term']['total_savings']
        long_total = recommendation['best_long_term']['total_savings']
        diff = long_total - short_total
        
        st.markdown(f"""
        **🤔 단기 vs 장기 비교**
        
        - 단기 효과 최대: **{format_currency(short_total)}** (총 절감)
        - 장기 효과 최대: **{format_currency(long_total)}** (총 절감)
        - 차이: **{format_currency(abs(diff))}**
        """)
        
        if diff > 1000000:
            st.warning(
                f"⚠️ 장기 효과가 단기보다 {format_currency(diff)} 더 큽니다. "
                f"이자율만 보지 말고 만기까지 남은 기간도 고려하세요!"
            )
    
    with insight_col2:
        # 만기 임박 대출 알림
        urgent = [s for s in simulations if 0 < s['months_until_maturity'] <= 6]
        if urgent:
            st.markdown("**⚠️ 만기 임박 대출**")
            for u in urgent:
                st.markdown(
                    f"- **{u['loan_name']}**: {u['months_until_maturity']}개월 남음 "
                    f"(잔액 {format_currency(u['current_balance'])})"
                )
            st.caption("💡 만기 시 일시 상환 부담 vs 연장 시 이자 부담 검토")
        else:
            st.markdown("**✅ 만기 임박 대출 없음**")
            st.caption("모든 대출의 만기가 6개월 이상 남아있어 여유가 있습니다.")
    
    # =========================================
    # 모든 대출 상세 비교
    # =========================================
    st.divider()
    st.markdown("### 📋 모든 대출 상세 비교")
    
    # 표 데이터 준비
    table_data = []
    for sim in simulations:
        table_data.append({
            "순위": "🥇" if sim == simulations[0] else ("🥈" if sim == simulations[1] else "🥉" if len(simulations) > 2 and sim == simulations[2] else f"{simulations.index(sim)+1}"),
            "대출명": sim['loan_name'],
            "금리": f"{sim['interest_rate']}% ({sim['rate_type']})",
            "현재 잔액": format_currency(sim['current_balance']),
            "상환 후 잔액": format_currency(sim['new_balance']),
            "월 절감": format_currency(sim['monthly_savings']),
            "만기까지": f"{sim['months_until_maturity']}개월" if sim['months_until_maturity'] > 0 else "지남",
            "총 절감": format_currency(sim['total_savings']),
        })
    
    df = pd.DataFrame(table_data)
    st.dataframe(df, hide_index=True, use_container_width=True)
    
    # =========================================
    # 대출별 상세 카드
    # =========================================
    st.divider()
    st.markdown("### 🔍 각 대출 상세 분석")
    
    for i, sim in enumerate(simulations):
        rank_emoji = "🥇" if i == 0 else ("🥈" if i == 1 else "🥉" if i == 2 else f"#{i+1}")
        rate_emoji = "🔴" if sim['interest_rate'] >= 5 else ("🟡" if sim['interest_rate'] >= 4 else "🟢")
        
        with st.expander(f"{rank_emoji} {rate_emoji} {sim['loan_name']} ({sim['interest_rate']}%)"):
            
            # 메트릭 4개
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    label="현재 잔액",
                    value=format_currency(sim['current_balance'])
                )
            
            with col2:
                st.metric(
                    label="상환 후 잔액",
                    value=format_currency(sim['new_balance']),
                    delta=f"-{format_currency(sim['repayment_amount'])}",
                    delta_color="inverse"
                )
            
            with col3:
                st.metric(
                    label="월 이자 절감",
                    value=format_currency(sim['monthly_savings'])
                )
            
            with col4:
                st.metric(
                    label="만기까지 총 절감",
                    value=format_currency(sim['total_savings'])
                )
            
            # 진행률 바
            current_progress = ((sim['current_balance'] / (sim['current_balance'] + (sim['current_balance'] - sim['new_balance']))) * 100) if sim['current_balance'] > 0 else 0
            new_progress = ((sim['new_balance'] / sim['current_balance']) * 100) if sim['current_balance'] > 0 else 0
            
            st.markdown(f"**상환 후 잔액 비율**: {new_progress:.1f}%")
            st.progress(1 - (new_progress / 100))
            
            # 추가 정보
            st.caption(
                f"📅 만기일: {sim['maturity_date']} ({sim['months_until_maturity']}개월 남음) | "
                f"💼 {sim['repayment_method']} | "
                f"📊 추천 점수: {sim['priority_score']:.1f}점"
            )
            
            if sim['is_paid_off']:
                st.success(f"🎉 이 금액으로 {sim['loan_name']}을(를) 완납할 수 있습니다!")
    
    # =========================================
    # 분산 상환 시나리오
    # =========================================
    st.divider()
    st.markdown("### 🎲 분산 상환 시나리오")
    st.caption("단일 대출이 아닌 여러 대출에 분산해서 갚는 시나리오를 비교해보세요.")
    
    with st.expander("✏️ 분산 상환 비율 입력", expanded=False):
        st.markdown(f"💰 총 가용 자금: **{format_currency(amount)}**")
        
        # 각 대출별 비율 슬라이더
        ratios = {}
        total_ratio = 0
        
        for sim in simulations:
            ratio = st.slider(
                f"{sim['loan_name']} ({sim['interest_rate']}%)",
                min_value=0,
                max_value=100,
                value=0,
                step=10,
                key=f"split_{sim['loan_id']}",
                help=f"이 대출에 가용 자금의 몇 %를 사용할지"
            )
            ratios[sim['loan_id']] = ratio
            total_ratio += ratio
        
        if total_ratio > 0:
            st.markdown(f"**합계: {total_ratio}%**")
            
            if total_ratio != 100:
                st.warning(f"⚠️ 비율 합계가 100%가 아닙니다. (현재: {total_ratio}%)")
            else:
                st.success("✅ 비율 합계가 100%입니다!")
                
                # 분산 시뮬레이션
                st.markdown("#### 📊 분산 상환 결과")
                
                total_monthly = 0
                total_long = 0
                
                for sim in simulations:
                    ratio = ratios[sim['loan_id']]
                    if ratio > 0:
                        loan_amount = amount * (ratio / 100)
                        loan = next((l for l in loans if l.loan_id == sim['loan_id']), None)
                        
                        if loan:
                            split_sim = simulate_partial_payment(loan, loan_amount)
                            total_monthly += split_sim['monthly_savings']
                            total_long += split_sim['total_savings']
                            
                            st.markdown(
                                f"- **{sim['loan_name']}**: "
                                f"{format_currency(loan_amount)} ({ratio}%) → "
                                f"월 절감 {format_currency(split_sim['monthly_savings'])}, "
                                f"총 절감 {format_currency(split_sim['total_savings'])}"
                            )
                
                st.divider()
                
                col_total1, col_total2 = st.columns(2)
                with col_total1:
                    st.metric(
                        label="💰 총 월 이자 절감",
                        value=format_currency(total_monthly)
                    )
                with col_total2:
                    st.metric(
                        label="📈 총 만기까지 절감",
                        value=format_currency(total_long)
                    )
                
                # 단일 상환 vs 분산 상환 비교
                best_single = recommendation['best_long_term']['total_savings']
                if total_long > best_single:
                    st.success(f"🎯 분산 상환이 단일 최고 ({format_currency(best_single)})보다 {format_currency(total_long - best_single)} 더 효율적!")
                elif total_long == best_single:
                    st.info("📊 단일 최고 상환과 동일한 효과")
                else:
                    st.warning(f"⚠️ 단일 최고 상환이 {format_currency(best_single - total_long)} 더 효율적")
    
    # =========================================
    # 사용 가이드
    # =========================================
    with st.expander("💡 시뮬레이터 사용 가이드"):
        st.markdown("""
        ### 활용 방법
        
        1. **가용 자금 입력**: 보너스, 적금 만기, 추가 수입 등 부분상환 가능한 금액
        2. **추천 확인**: 종합/단기/장기 3가지 관점의 추천 비교
        3. **상세 분석**: 각 대출별 효과 자세히 살펴보기
        4. **분산 시나리오**: 여러 대출에 나눠 갚을 때 효과 시뮬레이션
        
        ### 추천 알고리즘 기준
        
        - **이자율** (가장 중요): 높을수록 우선
        - **만기 임박**: 6개월 이내 만기 시 가산점
        - **변동금리**: 금리 인상 위험으로 가산점
        
        ### 의사결정 팁
        
        - **단기 효과 (월 절감)**: 즉시 가계 부담 감소
        - **장기 효과 (총 절감)**: 5년~30년 누적 효과
        - **균형**: 만기 임박 + 큰 잔액 둘 다 고려
        - **분산**: 위험 분산 + 효과 극대화
        
        ### 추천 vs 실제 결정
        
        시뮬레이터는 **수치 계산**만 합니다. 다음도 고려하세요:
        - 비상 자금 보유
        - 다른 투자 기회
        - 세금 혜택 (주담대 이자 소득공제 등)
        """)


if __name__ == "__main__":
    render_simulator()