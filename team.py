# 한국 전체 확진자 증가수 (너무 급격하게 오르지 않게하기 위해 log 스케일로 표현)
# 대구 지역 확진자 증가수 (초반에 가장 많이 올랐기 때문에)
# 한국 전체와 대구지역 비교 
# 위에 세개를 버튼을 이용해서 한 그래프에
# 현식님 3d 지도히트맵을 이용해서 시기별 확진자 시각화

# import libraries
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio


# 데이터 전처리
# 한국 종합 데이터
df_total = pd.read_csv("data/kr_daily.csv")  # 한국 종합 데이터 로드
df_total["date"] = pd.to_datetime(df_total["date"], format="%Y%m%d") # 날짜 형식 변환 및 정렬
df_total = df_total.sort_values("date").reset_index(drop=True) # 날짜순 정렬
df_total["critical"] = df_total["critical"].fillna(0) # 결측치 0으로 채우기
# 일별 증감 계산
cols = ["confirmed", "death", "released", "tested", "negative", "critical"]
new_cols = df_total[cols].diff() # 일별 차이는 new_를 붙혀서 새로운 컬럼으로 표현
new_cols.columns = ["new_" + c for c in cols]
df_total = pd.concat([df_total, new_cols], axis=1) # 기존데이터 프레임에 새로운 컬럼 추가
df_total.fillna(0, inplace=True) # 첫 행 NaN 제거

print(df_total.columns)

# 지역별 데이터
df = pd.read_csv("data/kr_regional_daily_excel.csv") # 지역별 데이터 로드
df["date"] = pd.to_datetime(df["date"], format="%Y%m%d") # 날짜 형식 변환 
df = df.sort_values(["region", "date"]).reset_index(drop=True) # 지역,날짜순 정렬
df["new_confirmed"] = (
    df.groupby("region")["confirmed"].diff().fillna(0).clip(lower=0) # 지역에 따른 일자별 신규확진자 컬럼 만들고 결측치 0으로 채우기
)

print(df.columns)


# 대구 지역 데이터 필터링
df_Daegu = df[df["region"]=="Daegu"][["date", "new_confirmed"]]
print(df_Daegu.head())


# 한국 전체 신규 확진자수 시각화
fig = go.Figure()
fig.add_trace(go.Scatter(x=df_total.date, y=df_total.new_confirmed,
                         mode='markers', name='한국 전체 신규 확진자 수',))
# 대구 지역 신규 확진자수 시각화
fig.add_trace(go.Scatter(x=df_Daegu.date, y=df_Daegu.new_confirmed,
                         mode='markers', name='대구 지역 신규 확진자 수')) 

# 그래프 레이아웃 설정
fig.update_layout(
    # 타이틀,축 지정
    title = "한국 전체, 대구 일별 신규 확진자수",
    xaxis_title="날짜",
    yaxis_title="신규 확진자 수",
    yaxis_type="log", # y축 로그스케일
    
    # legend 레이아웃 지정
    legend_x=0.85,
    legend_y=0.95,
    legend_bordercolor="Black",
    legend_borderwidth=2,
    
    # hover 레이아웃 지정
    hovermode="x unified",# 날짜에 따라서 hovermode 작동
    
    # 버튼 생성
    updatemenus=[
      dict(
        type = "dropdown",
        direction = "down",
        buttons = list([
            dict(
                label = "한국 전체 신규 확진자 수",
                method = "update",
                args = [{"visible": [True, False]},
                        {"title": "한국 전체 신규 확진자 수"}]
            ),
            dict(
                label = "한국 전체, 대구 일별 확진자 수",
                method = "update",
                args = [{"visible": [True, True]},
                        {"title": "한국 전체, 대구 일별 신규 확진자수"}]
            )
        ]),
      )
    ]
)
# 모드 바 편집 - 그림그리는거 추가
"""fig.show(config = {'modeBarButtonsToAdd': ['drawline','drawopenpath','drawclosedpath',
                             'drawcircle','drawrect','eraseshape']}) # 나중에 그림파일로 다운로드 ?"""




# 지도 html 파일과 그래프 html 파일을 합쳐서 하나의 대시보드 html 파일로 만들기
line_html = fig.to_html(
    full_html=False,
    include_plotlyjs="cdn",
    default_height="85vh",
    config={'modeBarButtonsToAdd': [
        'drawline','drawopenpath','drawclosedpath',
        'drawcircle','drawrect','eraseshape'
    ]}
)


map_file = "코로나대시보드/covid_map.html"          # 기존 버튼
other_file = "코로나대시보드/other_page.html"       # ✅ 추가할 버튼(여기에 새 html 경로 넣기)

final_html = f"""
<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <title>COVID Dashboard</title>
  <style>
    body {{ margin:0; padding:10px; background:#f4f4f9; font-family: Arial, sans-serif; }}
    .bar {{ display:flex; gap:8px; margin-bottom:10px; }}
    .bar button {{
      padding:8px 12px; border:1px solid #ccc; border-radius:6px;
      background:white; cursor:pointer; font-weight:600;
    }}
  </style>
</head>
<body>
  <div class="bar">
    <button onclick="window.open('{map_file}', '_blank')">confirmed_maps</button>
    <button onclick="window.open('{other_file}', '_blank')">other_page</button>  <!-- ✅ 추가 -->
  </div>

  {line_html}
</body>
</html>
"""

with open("covid_teamdashboard.html", "w", encoding="utf-8") as f:
    f.write(final_html)


