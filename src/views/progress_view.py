"""
5년 진행 그래프 화면 (Streamlit)
- 잔액 추이 그래프
- 5년 목표 달성 예측
- 대출별 잔액 추이
- 월별 상환액
"""

import streamlit as st
import pandas as pd
from datetime import date, datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.services.progress_analyzer import (
    get_total_balance,
    get_total_initial,
    get_total_repaid,
    get_monthly_balance_history,
    calculate_average_monthly_repayment,
    estimate_target_completion,
    get_projection_data,
    get_loan_breakdown_history,
    TARGET_BALANCE,
    PROJECT_END_DATE,
)
from src.services.loan_repository import get_active_loans, get_all_loans
from src.utils.helpers import format_currency


def render_progress_view():
    """5년 진행 그래프 화면"""
    
    st.title("📈 5년 진행 그래프")
    st.caption("부부의 5년 부채 청산 여정을 시각적으로 확인하고, 목표 달성 가능성을 예측합니다.")
    
    # 기본 데이터
    current_balance = get_total_balance()
    total_initial = get_total_initial()
    total_repaid = get_total_repaid()
    progress_percent = (total_repaid / total_initial * 100) if total_initial > 0 else 0
    
    # 5년 목표
    estimation = estimate_target_completion()
    
    # =========================================
    # 핵심 지표
    # =========================================
    st.divider()
    st.markdown("### 📊 핵심 지표")
    
    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    
    with metric_col1:
        st.metric(
            label="📊 현재 잔액",
            value=format_currency(current_balance),
            delta=f"-{format_currency(total_repaid)} 상환",
            delta_color="inverse"
        )
    
    with metric_col2:
        st.metric(
            label="🎯 5년 목표",
            value=format_currency(TARGET_BALANCE),
            delta=f"-{format_currency(estimation['remaining'])} 남음",
            delta_color="inverse"
        )
    
    with metric_col3:
        st.metric(
            label="📈 현재 진행률",
            value=f"{progress_percent:.1f}%",
            delta=f"목표 95.6%까지 {95.6 - progress_percent:.1f}%p"
        )
    
    with metric_col4:
        avg_monthly = estimation['avg_monthly_repayment']
        if avg_monthly > 0:
            st.metric(
                label="💰 월 평균 상환",
                value=format_currency(avg_monthly),
                help="최근 6개월 평균"
            )
        else:
            st.metric(
                label="💰 월 평균 상환",
                value="데이터 없음",
                help="첫 상환 입력 후 계산됩니다"
            )
    
    st.divider()
    
    # =========================================
    # 5년 목표 달성 예측
    # =========================================
    st.markdown("### 🎯 5년 목표 달성 예측")
    
    if avg_monthly > 0:
        if estimation['will_achieve']:
            st.success(
                f"✅ **현재 페이스로 5년 목표 달성 가능!**\n\n"
                f"- 현재 페이스: 월 평균 {format_currency(avg_monthly)} 상환\n"
                f"- 현재 페이스로 목표까지: 약 {estimation['months_at_current_pace']:.1f}개월\n"
                f"- 5년 목표일까지: {estimation['months_to_target_date']}개월"
            )
        else:
            shortfall = estimation['shortfall']
            extra_monthly = shortfall / max(1, estimation['months_to_target_date'])
            st.warning(
                f"⚠️ **현재 페이스로는 5년 목표 달성이 어려워요.**\n\n"
                f"- 현재 페이스: 월 평균 {format_currency(avg_monthly)} 상환\n"
                f"- 부족분: {format_currency(shortfall)}\n"
                f"- 추가 필요 월 상환: 약 {format_currency(extra_monthly)}/월\n\n"
                f"💡 **해결책**: 보너스, 적금 만기 자금 등으로 부분 상환을 추가하세요!"
            )
    else:
        st.info(
            "ℹ️ **아직 상환 데이터가 없어 예측이 어려워요.**\n\n"
            "5월 10일 첫 정기상환 후 다시 확인하시면 정확한 예측이 가능합니다."
        )
    
    st.divider()
    
    # =========================================
    # 메인 그래프: 잔액 추이
    # =========================================
    st.markdown("### 📈 잔액 추이 (과거 + 미래 예측)")
    
    # 과거 데이터
    history = get_monthly_balance_history()
    
    # 미래 예측
    projections = get_projection_data(months_ahead=60)
    
    # 그래프용 데이터 준비
    fig = go.Figure()
    
    # 과거 데이터 추가
    if history:
        history_df = pd.DataFrame(history)
        history_df['date'] = pd.to_datetime(history_df['month'] + '-01')
        
        fig.add_trace(go.Scatter(
            x=history_df['date'],
            y=history_df['balance'],
            mode='lines+markers',
            name='실제 잔액',
            line=dict(color='#FF6B6B', width=3),
            marker=dict(size=10, color='#FF6B6B'),
            hovertemplate='<b>%{x|%Y년 %m월}</b><br>잔액: %{y:,.0f}원<extra></extra>'
        ))
    
    # 미래 예측 추가
    if projections and avg_monthly > 0:
        proj_df = pd.DataFrame(projections)
        proj_df['date'] = pd.to_datetime(proj_df['month'] + '-01')
        
        # 현재 시점부터 시작하도록 첫 점 추가
        if history:
            proj_df = pd.concat([
                pd.DataFrame([{
                    'month': history_df.iloc[-1]['month'],
                    'date': history_df.iloc[-1]['date'],
                    'projected_balance': history_df.iloc[-1]['balance']
                }]),
                proj_df
            ], ignore_index=True)
        
        fig.add_trace(go.Scatter(
            x=proj_df['date'],
            y=proj_df['projected_balance'],
            mode='lines',
            name='예상 잔액 (현재 페이스)',
            line=dict(color='#4ECDC4', width=2, dash='dash'),
            hovertemplate='<b>%{x|%Y년 %m월}</b><br>예상 잔액: %{y:,.0f}원<extra></extra>'
        ))
    
    # 5년 목표 잔액 (가로선)
    fig.add_hline(
        y=TARGET_BALANCE,
        line_dash="dot",
        line_color="#95E1D3",
        annotation_text=f"🎯 5년 목표: {format_currency(TARGET_BALANCE)}",
        annotation_position="right"
    )
    
    # 5년 종료일 (세로선) - shapes로 처리하여 호환성 확보
    end_date = pd.to_datetime(PROJECT_END_DATE)
    fig.add_shape(
        type="line",
        x0=end_date,
        x1=end_date,
        y0=0,
        y1=1,
        yref="paper",
        line=dict(color="#FFA07A", width=2, dash="dot"),
    )
    fig.add_annotation(
        x=end_date,
        y=1,
        yref="paper",
        text="📅 5년 종료",
        showarrow=False,
        yshift=10,
        font=dict(color="#FFA07A", size=12),
    )
    
    # 레이아웃
    fig.update_layout(
        title="💪 5년 부채 청산 여정",
        xaxis_title="시점",
        yaxis_title="잔액 (원)",
        hovermode='x unified',
        height=500,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        yaxis=dict(
            tickformat=',.0f',
        )
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    
    # =========================================
    # 대출별 잔액 추이
    # =========================================
    st.markdown("### 📊 대출별 잔액 추이")
    
    breakdown = get_loan_breakdown_history()
    
    if breakdown and any(history for history in breakdown.values()):
        # 각 대출별 그래프
        fig2 = go.Figure()
        
        colors = ['#FF6B6B', '#4ECDC4', '#FFD93D', '#95E1D3', '#FFA07A']
        
        all_loans = get_all_loans()
        for i, loan in enumerate(all_loans):
            loan_history = breakdown.get(loan.loan_name, [])
            
            if loan_history:
                df = pd.DataFrame(loan_history)
                df['date'] = pd.to_datetime(df['month'] + '-01')
                
                fig2.add_trace(go.Scatter(
                    x=df['date'],
                    y=df['balance'],
                    mode='lines+markers',
                    name=loan.loan_name,
                    line=dict(color=colors[i % len(colors)], width=2),
                    hovertemplate=f'<b>{loan.loan_name}</b><br>%{{x|%Y년 %m월}}<br>잔액: %{{y:,.0f}}원<extra></extra>'
                ))
            else:
                # 데이터 없으면 현재 잔액 한 점만
                today = date.today()
                fig2.add_trace(go.Scatter(
                    x=[today],
                    y=[loan.current_balance],
                    mode='markers',
                    name=loan.loan_name,
                    marker=dict(size=12, color=colors[i % len(colors)]),
                    hovertemplate=f'<b>{loan.loan_name}</b><br>현재 잔액: %{{y:,.0f}}원<extra></extra>'
                ))
        
        fig2.update_layout(
            title="대출별 잔액 변화",
            xaxis_title="시점",
            yaxis_title="잔액 (원)",
            hovermode='x unified',
            height=400,
            yaxis=dict(tickformat=',.0f')
        )
        
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("ℹ️ 대출별 상세 추이는 상환 이력이 누적되면 표시됩니다.")
    
    st.divider()
    
    # =========================================
    # 월별 상환액 (막대 그래프)
    # =========================================
    st.markdown("### 📊 월별 상환액")
    
    if history:
        df = pd.DataFrame(history)
        df['date'] = pd.to_datetime(df['month'] + '-01')
        
        fig3 = go.Figure()
        
        fig3.add_trace(go.Bar(
            x=df['date'],
            y=df['monthly_principal'],
            name='원금',
            marker_color='#FF6B6B',
            hovertemplate='<b>%{x|%Y년 %m월}</b><br>원금: %{y:,.0f}원<extra></extra>'
        ))
        
        fig3.add_trace(go.Bar(
            x=df['date'],
            y=df['monthly_interest'],
            name='이자',
            marker_color='#FFD93D',
            hovertemplate='<b>%{x|%Y년 %m월}</b><br>이자: %{y:,.0f}원<extra></extra>'
        ))
        
        fig3.update_layout(
            title="월별 원금/이자 상환",
            xaxis_title="월",
            yaxis_title="금액 (원)",
            barmode='stack',
            height=350,
            yaxis=dict(tickformat=',.0f')
        )
        
        st.plotly_chart(fig3, use_container_width=True)
        
        # 통계 요약
        total_p = sum(h['monthly_principal'] for h in history)
        total_i = sum(h['monthly_interest'] for h in history)
        
        sum_col1, sum_col2, sum_col3 = st.columns(3)
        
        with sum_col1:
            st.metric("누적 원금", format_currency(total_p))
        with sum_col2:
            st.metric("누적 이자", format_currency(total_i))
        with sum_col3:
            st.metric("누적 총액", format_currency(total_p + total_i))
    else:
        st.info("ℹ️ 첫 상환 입력 후 월별 상환액 그래프가 표시됩니다.")
    
    st.divider()
    
    # =========================================
    # 동기부여 메시지
    # =========================================
    st.markdown("### 💪 동기부여")
    
    motivation_col1, motivation_col2 = st.columns(2)
    
    with motivation_col1:
        if progress_percent < 25:
            st.info(
                "🌱 **시작이 반!** 부부의 5년 여정이 시작됐어요.\n\n"
                "꾸준함이 가장 중요합니다. 매월 정기상환을 입력하며 진척도를 함께 확인하세요."
            )
        elif progress_percent < 50:
            st.info(
                "🚀 **잘 가고 있어요!** 이미 4분의 1 이상 갚았네요.\n\n"
                "지금처럼 꾸준히 가면 5년 목표 달성 가능합니다."
            )
        elif progress_percent < 75:
            st.success(
                "💪 **절반을 넘었어요!** 정말 대단하시네요.\n\n"
                "후반전입니다. 마지막까지 꾸준히 가시면 됩니다!"
            )
        else:
            st.success(
                "🎯 **거의 다 왔어요!** 마지막 25%만 남았네요.\n\n"
                "조금만 더 힘내시면 5년 목표 달성!"
            )
    
    with motivation_col2:
        st.markdown(f"""
        **🎯 다음 목표:**
        
        {f"- 다음 25% 달성까지: {format_currency(total_initial * 0.25 - total_repaid)}" if progress_percent < 25 else ""}
        {f"- 절반 (50%) 달성까지: {format_currency(total_initial * 0.50 - total_repaid)}" if 25 <= progress_percent < 50 else ""}
        {f"- 75% 달성까지: {format_currency(total_initial * 0.75 - total_repaid)}" if 50 <= progress_percent < 75 else ""}
        {f"- 5년 목표 달성까지: {format_currency(estimation['remaining'])}" if progress_percent >= 75 else ""}
        
        **⏰ 남은 시간:**
        - 5년 목표일까지: **{estimation['months_to_target_date']}개월**
        - = **약 {estimation['months_to_target_date'] / 12:.1f}년**
        """)


if __name__ == "__main__":
    render_progress_view()