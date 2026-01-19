import pandas as pd
import app as st
import plotly.express as px
from pathlib import Path

# ======================
# 기본 설정
# ======================
st.set_page_config(
    page_title="사내 인사 & 마케팅 통합 대시보드",
    page_icon="📊",
    layout="wide"
)

# ======================
# 데이터 로드 함수
# ======================
@st.cache_data
def load_data():
    base_path = Path(__file__).resolve().parent
    hr_path = base_path / "data" / "HR.csv"
    mkt_path = base_path / "data" / "marketing.csv"

    hr = pd.read_csv(hr_path)
    mkt = pd.read_csv(mkt_path)

    # 날짜 컬럼 변환 (있을 경우)
    for col in ["join_date", "leave_date"]:
        if col in hr.columns:
            hr[col] = pd.to_datetime(hr[col], errors="coerce")

    if "date" in mkt.columns:
        mkt["date"] = pd.to_datetime(mkt["date"], errors="coerce")

    return hr, mkt


# ======================
# 유틸 함수
# ======================
def calc_hr_metrics(hr_filtered):
    # 퇴사 여부 플래그
    if "leave_date" in hr_filtered.columns:
        left_flag = hr_filtered["leave_date"].notna()
    else:
        left_flag = pd.Series(False, index=hr_filtered.index)

    total_emp = len(hr_filtered)
    left_emp = left_flag.sum()
    turnover_rate = (left_emp / total_emp * 100) if total_emp > 0 else 0

    return {
        "total_emp": total_emp,
        "left_emp": left_emp,
        "turnover_rate": turnover_rate
    }


def calc_marketing_metrics(mkt_filtered):
    total_spend = mkt_filtered["spend"].sum() if "spend" in mkt_filtered.columns else 0
    total_revenue = mkt_filtered["revenue"].sum() if "revenue" in mkt_filtered.columns else 0

    # ROI = (Revenue - Spend) / Spend
    if total_spend > 0:
        roi = (total_revenue - total_spend) / total_spend * 100
    else:
        roi = 0

    total_conv = mkt_filtered["conversions"].sum() if "conversions" in mkt_filtered.columns else 0
    total_impr = mkt_filtered["impressions"].sum() if "impressions" in mkt_filtered.columns else 0

    # 전환율 = conversions / impressions
    conv_rate = (total_conv / total_impr * 100) if total_impr > 0 else 0

    return {
        "total_spend": total_spend,
        "total_revenue": total_revenue,
        "roi": roi,
        "conv_rate": conv_rate
    }


# ======================
# 메인
# ======================
def main():
    # -------- 사이드바 --------
    st.sidebar.image(
        "https://static.streamlit.io/examples/dice.jpg",
        width=120,
        caption="Company Logo (예시)"
    )

    st.sidebar.title("필터")

    # 데이터 로드
    hr, mkt = load_data()

    # 공통/HR 필터
    dept_list = sorted(hr["department"].dropna().unique()) if "department" in hr.columns else []
    selected_dept = st.sidebar.multiselect("부서 선택", dept_list, default=dept_list)

    # 마케팅 필터
    channel_list = sorted(mkt["channel"].dropna().unique()) if "channel" in mkt.columns else []
    selected_channel = st.sidebar.multiselect("마케팅 채널 선택", channel_list, default=channel_list)

    # 날짜 범위 (마케팅)
    if "date" in mkt.columns and not mkt["date"].isna().all():
        min_date = mkt["date"].min()
        max_date = mkt["date"].max()
        date_range = st.sidebar.date_input(
            "캠페인 기간",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )
    else:
        date_range = None

    # 필터 적용
    hr_filtered = hr.copy()
    if selected_dept and "department" in hr.columns:
        hr_filtered = hr_filtered[hr_filtered["department"].isin(selected_dept)]

    mkt_filtered = mkt.copy()
    if selected_channel and "channel" in mkt.columns:
        mkt_filtered = mkt_filtered[mkt_filtered["channel"].isin(selected_channel)]

    if date_range and "date" in mkt_filtered.columns:
        start, end = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
        mkt_filtered = mkt_filtered[(mkt_filtered["date"] >= start) & (mkt_filtered["date"] <= end)]

    # -------- 페이지 타이틀 / 개요 --------
    st.title("사내 인사 및 마케팅 현황 통합 모니터링 대시보드")
    st.markdown(
        """
        **개요**  
        - 인사(HR) 및 마케팅 데이터를 통합하여 한 화면에서 모니터링할 수 있는 웹 대시보드입니다.  
        - 사이드바 필터를 통해 부서, 채널, 기간 등을 조정하면서 KPI 및 시각화를 탐색할 수 있습니다.  
        """
    )

    # -------- 탭 구성 --------
    tab_hr, tab_mkt = st.tabs(["👥 HR 대시보드", "📣 마케팅 대시보드"])

    # ======================
    # HR 탭
    # ======================
    with tab_hr:
        st.subheader("HR 현황")

        metrics = calc_hr_metrics(hr_filtered)

        col1, col2, col3 = st.columns(3)
        col1.metric("총 인원 수", f"{metrics['total_emp']:,}")
        col2.metric("퇴사 인원 수", f"{metrics['left_emp']:,}")
        col3.metric("퇴사율 (%)", f"{metrics['turnover_rate']:.1f}%")

        st.markdown("---")

        # 부서별 현황 (Bar)
        st.markdown("### 부서별 인원 현황")
        if "department" in hr_filtered.columns:
            dept_summary = (
                hr_filtered
                .groupby("department")
                .agg(
                    headcount=("employee_id", "count") if "employee_id" in hr_filtered.columns else ("department", "count"),
                    avg_salary=("salary", "mean") if "salary" in hr_filtered.columns else ("department", "count")
                )
                .reset_index()
            )

            fig_dept = px.bar(
                dept_summary,
                x="department",
                y="headcount",
                color="department",
                title="부서별 인원수",
                text_auto=True
            )
            fig_dept.update_layout(xaxis_title="부서", yaxis_title="인원수", showlegend=False)
            st.plotly_chart(fig_dept, use_container_width=True)
        else:
            st.info("`department` 컬럼이 없어 부서별 현황을 표시할 수 없습니다.")

        st.markdown("---")

        # 소득 관계(Box) - 예: 부서별 급여 분포
        st.markdown("### 부서별 급여 분포 (Box Plot)")
        if "salary" in hr_filtered.columns and "department" in hr_filtered.columns:
            fig_salary = px.box(
                hr_filtered,
                x="department",
                y="salary",
                color="department",
                title="부서별 급여 분포",
            )
            fig_salary.update_layout(xaxis_title="부서", yaxis_title="급여", showlegend=False)
            st.plotly_chart(fig_salary, use_container_width=True)
        else:
            st.info("`salary` 또는 `department` 컬럼이 없어 급여 분포를 표시할 수 없습니다.")

    # ======================
    # 마케팅 탭
    # ======================
    with tab_mkt:
        st.subheader("마케팅 성과")

        mkt_metrics = calc_marketing_metrics(mkt_filtered)

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("총 집행비 (Spend)", f"{mkt_metrics['total_spend']:,.0f}")
        col2.metric("총 매출 (Revenue)", f"{mkt_metrics['total_revenue']:,.0f}")
        col3.metric("ROI (%)", f"{mkt_metrics['roi']:.1f}%")
        col4.metric("전환율 (%)", f"{mkt_metrics['conv_rate']:.2f}%")

        st.markdown("---")

        # 채널별 전환율 (Bar / Scatter 모두 가능, 여기선 Bar)
        st.markdown("### 채널별 전환율")
        if {"channel", "conversions", "impressions"}.issubset(mkt_filtered.columns):
            channel_perf = (
                mkt_filtered
                .groupby("channel")
                .agg(
                    conversions=("conversions", "sum"),
                    impressions=("impressions", "sum"),
                    spend=("spend", "sum") if "spend" in mkt_filtered.columns else ("impressions", "sum"),
                    revenue=("revenue", "sum") if "revenue" in mkt_filtered.columns else ("impressions", "sum")
                )
                .reset_index()
            )
            channel_perf["conversion_rate"] = channel_perf.apply(
                lambda r: (r["conversions"] / r["impressions"] * 100) if r["impressions"] > 0 else 0,
                axis=1
            )

            fig_conv = px.bar(
                channel_perf,
                x="channel",
                y="conversion_rate",
                color="channel",
                text_auto=".1f",
                title="채널별 전환율 (%)"
            )
            fig_conv.update_layout(xaxis_title="채널", yaxis_title="전환율(%)", showlegend=False)
            st.plotly_chart(fig_conv, use_container_width=True)
        else:
            st.info("`channel`, `conversions`, `impressions` 컬럼이 필요합니다.")

        st.markdown("---")

        # 예산 효율성 (Scatter) - x: Spend, y: Revenue, 색: Channel, 크기: Conversions
        st.markdown("### 예산 효율성 (Spend vs Revenue)")
        if {"spend", "revenue"}.issubset(mkt_filtered.columns):
            fig_roi = px.scatter(
                mkt_filtered,
                x="spend",
                y="revenue",
                color="channel" if "channel" in mkt_filtered.columns else None,
                size="conversions" if "conversions" in mkt_filtered.columns else None,
                hover_data=["campaign"] if "campaign" in mkt_filtered.columns else None,
                title="캠페인별 예산 효율성 (Scatter Plot)",
            )
            fig_roi.update_layout(xaxis_title="집행비 (Spend)", yaxis_title="매출 (Revenue)")
            st.plotly_chart(fig_roi, use_container_width=True)
        else:
            st.info("`spend`, `revenue` 컬럼이 필요합니다.")


if __name__ == "__main__":
    main()