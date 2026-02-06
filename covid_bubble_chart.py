# -*- coding: utf-8 -*-
"""covid_bubble_chart.py

대한민국 코로나19 지역별 Bubble Chart (Plotly + Dash)

✅ VSCode에서 "화면 버튼(지역 선택) + 확인"을 구현하려면?
- plotly의 fig.show()만으로는, 사용자가 브라우저에서 클릭한 값을 Python이 받을 수 없습니다.
- Dash는 웹 UI 이벤트(드롭다운/체크/버튼 클릭)를 Python 콜백 함수가 받아서
  데이터 재계산(집계/스케일/축 재구성) 후 그래프를 다시 그릴 수 있게 해줍니다.

✅ 이 스크립트가 하는 일
1) kr_regional_daily_excel.csv(누적 데이터)를 전처리
   - date: YYYY-MM-DD
   - region: 첫 단어만, 첫 글자 대문자 / Quarantine 제거
   - 누락 날짜: 직전 누적값으로 채움(ffill)
   - 누적 -> 일일 증분(confirm1/death1/released1)
2) 전처리 결과를 kr_covid_temp.txt로 저장
3) Dash 웹앱 실행
   - 드롭다운1: 확진자/사망자/완치자
   - 드롭다운2: 매일/주간/월간/분기ㅔㅛ
   - 지역 선택(체크리스트) + [확인] 버튼
   - 선택된 지역에 맞춰 Y축 재구성 + 버블 크기(sqrt 스케일) 재계산

실행 방법
- 설치:
    pip install pandas numpy plotly dash
- 실행:
    python covid_bubble_chart.py
- 브라우저:
    http://127.0.0.1:8050
"""

# ============================================================
# 0) Imports (파일 최상단)
# ============================================================
from pathlib import Path
import webbrowser
import threading

import pandas as pd
import numpy as np

import plotly.express as px
import plotly.graph_objects as go

from dash import Dash, dcc, html
from dash.dependencies import Input, Output, State


# ============================================================
# 1) 전처리: CSV(누적) -> 일일 증분 + 누락 날짜 보정 + 파일 저장
# ============================================================
def preprocess_and_save(
    input_csv: str = "data/kr_regional_daily_excel.csv",
    output_txt: str = "kr_covid_temp.txt",
) -> pd.DataFrame:
    """요구사항의 전처리를 수행하고 결과를 파일로 저장합니다."""

    # (1) CSV 읽기
    df = pd.read_csv(input_csv)

    # (2) date 처리: YYYYMMDD -> datetime -> YYYY-MM-DD
    df["date"] = df["date"].astype(str).str.strip()
    df["date_dt"] = pd.to_datetime(df["date"], format="%Y%m%d", errors="coerce")
    df = df.dropna(subset=["date_dt"]).copy()
    df["date1"] = df["date_dt"].dt.strftime("%Y-%m-%d")

    # (3) region 처리: 첫 단어만 + 첫 글자 대문자 / Quarantine 제거
    def normalize_region(x) -> str:
        token = str(x).strip().split()[0]
        return token.lower().capitalize()

    df["region1"] = df["region"].apply(normalize_region)
    df = df[df["region1"] != "Quarantine"].copy()

    # (4) 누적 컬럼을 숫자로 변환
    for c in ["confirmed", "death", "released"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # (5) 지역별 누락 날짜 보정
    all_dates = pd.date_range(df["date_dt"].min(), df["date_dt"].max(), freq="D")

    filled = []
    for region, g in df.sort_values("date_dt").groupby("region1"):
        # 지역별로 전체 날짜에 맞춰 재색인
        g = g.set_index("date_dt").reindex(all_dates)
        g["region1"] = region

        # 누적값은 직전값으로 채우기 (요구사항)
        g[["confirmed", "death", "released"]] = (
            g[["confirmed", "death", "released"]].ffill().fillna(0)
        )

        g = g.reset_index().rename(columns={"index": "date_dt"})
        g["date1"] = g["date_dt"].dt.strftime("%Y-%m-%d")
        filled.append(g)

    df_full = pd.concat(filled, ignore_index=True)
    df_full = df_full.sort_values(["region1", "date_dt"]).copy()

    # (6) 누적 -> 일일 증분(차이)
    delta = df_full.groupby("region1")[["confirmed", "death", "released"]].diff()

    # 지역별 첫날은 diff가 NaN → 누적값 자체 사용
    first_mask = df_full.groupby("region1").cumcount().eq(0)
    delta.loc[first_mask, :] = df_full.loc[first_mask, ["confirmed", "death", "released"]].values

    # 음수(정정 데이터) 방지
    delta = delta.clip(lower=0)

    df_full["confirm1"] = delta["confirmed"].round().astype(int)
    df_full["death1"] = delta["death"].round().astype(int)
    df_full["released1"] = delta["released"].round().astype(int)

    out = df_full[["date1", "region1", "confirm1", "death1", "released1"]].copy()

    # (2) 파일 저장
    out.to_csv(output_txt, index=False, sep=",")
    return out


# ============================================================
# 2) 기간 집계: 매일/주간/월간/분기
# ============================================================
def aggregate_by_period(df: pd.DataFrame, period: str) -> pd.DataFrame:
    """period(day/weekly/monthly/quarterly)에 따라 합계를 집계합니다."""
    temp = df.copy()
    temp["date_dt"] = pd.to_datetime(temp["date1"])  # 집계용 datetime

    if period == "day":
        return temp.groupby(["region1", "date_dt"], as_index=False)[["confirm1", "death1", "released1"]].sum()

    if period == "weekly":
        # 주 시작(월요일)으로 정규화
        temp["date_dt"] = temp["date_dt"] - pd.to_timedelta(temp["date_dt"].dt.weekday, unit="D")
        return temp.groupby(["region1", "date_dt"], as_index=False)[["confirm1", "death1", "released1"]].sum()

    if period == "monthly":
        temp["date_dt"] = temp["date_dt"].dt.to_period("M").dt.to_timestamp()
        return temp.groupby(["region1", "date_dt"], as_index=False)[["confirm1", "death1", "released1"]].sum()

    if period == "quarterly":
        temp["date_dt"] = temp["date_dt"].dt.to_period("Q").dt.to_timestamp()
        return temp.groupby(["region1", "date_dt"], as_index=False)[["confirm1", "death1", "released1"]].sum()

    raise ValueError("period must be one of: day, weekly, monthly, quarterly")


# ============================================================
# 3) 버블 크기: sqrt 스케일 + 선택된 값 범위(min/max)로 다시 스케일
# ============================================================
def make_marker_arrays(values: np.ndarray, min_px: int = 6, max_px: int = 85):
    """버블 크기/투명도/hover용 customdata 생성.

    - sqrt 스케일: 큰 값이 너무 커지는 문제를 줄임
    - BUT hover는 실제 값이 필요 → customdata[0]에 원본 값 저장
    - 0 값은 표시하지 않음(opacity=0)
    - 선택된 데이터 범위(min/max)를 기준으로 size를 매번 다시 스케일(극적 표현)
    """
    v = np.asarray(values, dtype=float)

    # hover에 쓸 실제 값 저장
    customdata = np.column_stack([v.astype(int)])

    # 0이면 완전 숨김
    opacity = np.where(v > 0, 0.85, 0.0)

    # sqrt 스케일(시각적 완화)
    s = np.sqrt(v)

    nz = s[v > 0]
    if len(nz) == 0:
        return np.zeros_like(s), opacity, customdata

    s_min, s_max = nz.min(), nz.max()
    if s_max == s_min:
        size = np.where(v > 0, (min_px + max_px) / 2, 0)
        return size, opacity, customdata

    # min~max 정규화 후 픽셀 크기로 맵핑
    size = np.where(
        v > 0,
        min_px + (s - s_min) / (s_max - s_min) * (max_px - min_px),
        0
    )
    return size, opacity, customdata


# ============================================================
# 4) Figure 생성: hover 텍스트(한글) 반영 + 제목 그래프 내부 + 타이틀 제거
# ============================================================
def build_figure(
    df_temp: pd.DataFrame,
    selected_regions: list[str],
    metric: str,
    period: str,
) -> go.Figure:
    """선택 조건에 맞춰 Figure를 새로 생성합니다."""

    # ----------------------------
    # (요구사항) 그래프 속성 정의
    # ----------------------------
    STYLE = {
        "title": "대한민국 코로나19",
        "gridcolor": "#F3F4F6",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "paper_bgcolor": "rgba(0,0,0,0)",
        "rangeslider_bgcolor": "white",

        # 제목을 그래프 영역 안쪽으로
        "title_y": 0.98,
        # 상단 여백(제목이 내부로 들어오더라도 공간 확보)
        "margin_top": 90,

        # 버블 크기 범위(극적 표현)
        "min_px": 6,
        "max_px": 85,
    }

    # ----------------------------
    # (요구사항) 드롭다운 값 -> 한글 라벨 매핑
    # - hover 텍스트도 이 라벨을 사용(요청사항)
    # ----------------------------
    METRIC_LABELS = {
        "confirm1": "확진자",
        "death1": "사망자",
        "released1": "완치자",
    }
    PERIOD_LABELS = {
        "day": "매일",
        "weekly": "주간",
        "monthly": "월간",
        "quarterly": "분기",
    }
    metric_label = METRIC_LABELS.get(metric, metric)
    period_label = PERIOD_LABELS.get(period, period)

    # ----------------------------
    # period 집계 후 지역 필터
    # ----------------------------
    agg = aggregate_by_period(df_temp, period)
    if selected_regions:
        agg = agg[agg["region1"].isin(selected_regions)].copy()

    # X축 MIN/MAX는 전체 date1 기준(요구사항)
    all_dt = pd.to_datetime(df_temp["date1"])
    x_min, x_max = all_dt.min(), all_dt.max()

    # Y축 카테고리는 선택 지역만
    regions = sorted(agg["region1"].unique())

    # region별 색상 고정
    all_regions = sorted(df_temp["region1"].unique())
    palette = px.colors.qualitative.Plotly
    color_map = {r: palette[i % len(palette)] for i, r in enumerate(all_regions)}

    fig = go.Figure()

    # region별 trace 생성
    for r in regions:
        sub = agg[agg["region1"] == r].sort_values("date_dt").copy()

        size, opacity, customdata = make_marker_arrays(
            sub[metric].values,
            min_px=STYLE["min_px"],
            max_px=STYLE["max_px"],
        )

        # -------------------------------------------------
        # ✅ Hover 텍스트(한글 라벨) 변경
        # - 'metric' 변수명(confirm1 등)이 아니라 '확진자/사망자/완치자'로 출력
        # - 'period'도 '매일/주간/월간/분기'로 출력
        # - 값은 customdata[0]로 실제값 표시(단위: 명)
        # -------------------------------------------------
        hover = (
            "날짜: %{x|%Y-%m-%d}<br>"
            "지역: %{y}<br>"
            + "기간: " + period_label + "<br>"
            + metric_label + ": %{customdata[0]}명"
            "<extra></extra>"
        )

        fig.add_trace(
            go.Scatter(
                x=sub["date_dt"],
                y=[r] * len(sub),
                mode="markers",
                name=r,
                marker=dict(
                    size=size,
                    opacity=opacity,
                    color=color_map.get(r, "#636EFA"),
                    sizemode="diameter",
                    sizemin=2,
                    line=dict(width=1, color=STYLE["gridcolor"])
                ),
                customdata=customdata,
                hovertemplate=hover,
            )
        )

    # 레이아웃: 제목 내부 배치, 타이틀 제거
    fig.update_layout(
        title=dict(
            text=STYLE["title"],
            x=0.5,
            xanchor="center",
            y=STYLE["title_y"],
            yanchor="top",
            font=dict(size=22)
        ),
        margin=dict(t=STYLE["margin_top"], r=30, b=60, l=90),
        plot_bgcolor=STYLE["plot_bgcolor"],
        paper_bgcolor=STYLE["paper_bgcolor"],

        xaxis=dict(
            title=None,
            gridcolor=STYLE["gridcolor"],
            showgrid=True,
            zeroline=False,
            range=[x_min, x_max],
            tickformat="%Y-%m-%d",
            rangeslider=dict(visible=True, bgcolor=STYLE["rangeslider_bgcolor"]),
        ),
        yaxis=dict(
            title=None,
            gridcolor=STYLE["gridcolor"],
            showgrid=True,
            zeroline=False,
            categoryorder="array",
            categoryarray=regions,
        ),
        legend=dict(
            title=None,
            itemclick="toggle",
            itemdoubleclick="toggleothers",
        ),
        hovermode="closest",
    )

    return fig


# ============================================================
# 5) Dash 앱 (VSCode 실행)
# ============================================================
#def run_dash_app(df_temp: pd.DataFrame):
    """Dash 앱 실행: 확인 버튼 클릭 시에만 그래프 업데이트."""
def run_dash_app(df_temp: pd.DataFrame, host: str = "127.0.0.1", port: int = 8050, open_browser: bool = True):
    # 드롭다운 라벨(요구사항)
    metric_options = [
        {"label": "확진자", "value": "confirm1"},
        {"label": "사망자", "value": "death1"},
        {"label": "완치자", "value": "released1"},
    ]
    period_options = [
        {"label": "매일", "value": "day"},
        {"label": "주간", "value": "weekly"},
        {"label": "월간", "value": "monthly"},
        {"label": "분기", "value": "quarterly"},
    ]

    all_regions = sorted(df_temp["region1"].unique())

    app = Dash(__name__)

    # Layout
    app.layout = html.Div(
        style={"fontFamily": "Arial", "padding": "12px"},
        children=[
            html.H3("대한민국 코로나19 Bubble Chart (VSCode + Dash)", style={"margin": "0 0 10px 0"}),

            html.Div(
                style={"display": "flex", "gap": "16px"},
                children=[
                    # 왼쪽 컨트롤 패널
                    html.Div(
                        style={
                            "width": "320px",
                            "border": "1px solid #E5E7EB",
                            "borderRadius": "10px",
                            "padding": "12px",
                            "backgroundColor": "white",
                        },
                        children=[
                            html.Div("지표", style={"fontWeight": "bold", "marginBottom": "6px"}),
                            dcc.Dropdown(id="metric", options=metric_options, value="confirm1", clearable=False),

                            html.Div(style={"height": "12px"}),

                            html.Div("기간", style={"fontWeight": "bold", "marginBottom": "6px"}),
                            dcc.Dropdown(id="period", options=period_options, value="day", clearable=False),

                            html.Div(style={"height": "12px"}),

                            html.Div("지역(복수 선택 가능)", style={"fontWeight": "bold", "marginBottom": "6px"}),
                            dcc.Checklist(
                                id="regions",
                                options=[{"label": r, "value": r} for r in all_regions],
                                value=all_regions,
                                labelStyle={"display": "block", "margin": "2px 0"},
                                inputStyle={"marginRight": "8px"},
                                style={"maxHeight": "360px", "overflowY": "auto", "padding": "6px"},
                            ),

                            html.Div(style={"height": "12px"}),

                            html.Button(
                                "확인",
                                id="apply",
                                n_clicks=0,
                                style={
                                    "width": "100%",
                                    "backgroundColor": "#2563EB",
                                    "color": "white",
                                    "border": "none",
                                    "borderRadius": "8px",
                                    "padding": "10px",
                                    "fontWeight": "bold",
                                    "cursor": "pointer",
                                },
                            ),

                            html.Div(
                                style={"marginTop": "10px", "fontSize": "12px", "color": "#6B7280"},
                                children=(
                                    "※ [확인] 클릭 시 선택 지역으로 Y축을 재구성하고, "
                                    "선택된 데이터의 min/max 기준으로 버블 크기를 다시 스케일링합니다."
                                ),
                            ),
                        ],
                    ),

                    # 오른쪽 그래프
                    html.Div(
                        style={"flex": "1", "minWidth": "700px"},
                        children=[
                            dcc.Graph(
                                id="chart",
                                figure=build_figure(df_temp, all_regions, "confirm1", "day"),
                                config={"displayModeBar": True},
                            )
                        ],
                    ),
                ],
            )
        ],
    )

    # Callback: 확인 버튼 클릭 시만 반영
    @app.callback(
        Output("chart", "figure"),
        Input("apply", "n_clicks"),
        State("regions", "value"),
        State("metric", "value"),
        State("period", "value"),
        prevent_initial_call=False,
    )
    def update_chart(n_clicks, selected_regions, metric, period):
        if not selected_regions:
            # 아무것도 선택 안 하면 최소 1개는 남기기
            selected_regions = [sorted(df_temp["region1"].unique())[0]]
        return build_figure(df_temp, selected_regions, metric, period)

    url = f"http://{host}:{port}"
    print("\n" + "=" * 70)
    print("✅ Dash 서버가 실행 중입니다. 아래 주소를 브라우저에서 여세요!")
    print(f"   {url}")
    print("   (종료: 터미널에서 CTRL + C)")
    print("=" * 70 + "\n")

    # 브라우저 자동 열기(사용자가 '바로 실행'처럼 느끼도록)
    if open_browser:
        def _open():
            # 서버가 뜨기 전에 브라우저가 열리면 접속 실패할 수 있으니 약간 지연
            import time
            time.sleep(1.0)
            webbrowser.open(url)

        threading.Thread(target=_open, daemon=True).start()

    #app.run(debug=False)
    app.run(host=host, port=port, debug=False)

# ============================================================
# 6) main
# ============================================================
if __name__ == "__main__":
    INPUT_CSV = "data/kr_regional_daily_excel.csv"
    OUTPUT_TXT = "kr_covid_temp.txt"

    # 전처리 파일이 없으면 생성
    if not Path(OUTPUT_TXT).exists():
        preprocess_and_save(INPUT_CSV, OUTPUT_TXT)

    # 가공 파일 읽기
    df_temp = pd.read_csv(OUTPUT_TXT)

    # Dash 앱 실행
    # run_dash_app(df_temp)
    # 바로 실행되게: 실행하면 브라우저 자동 오픈
    run_dash_app(df_temp, host="127.0.0.1", port=8050, open_browser=True)