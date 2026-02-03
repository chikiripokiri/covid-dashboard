import pandas as pd
import numpy as np
import plotly.graph_objects as go


# 한국 종합 데이터 로드
df_total = pd.read_csv("kr_daily.csv") 
# 날짜 형식 변환 및 정렬
df_total["date"] = pd.to_datetime(df_total["date"], format="%Y%m%d")
df_total = df_total.sort_values("date").reset_index(drop=True)

df_total["critical"] = df_total["critical"].fillna(0) # 결측치 0으로 채우기

# 일별 증감 계산
cols = ["confirmed", "death", "released", "tested", "negative", "critical"]
new_cols = df_total[cols].diff() # 일별 차이는 new_를 붙혀서 새로운 컬럼으로 표현
new_cols.columns = ["new_" + c for c in cols]

df_total = pd.concat([df_total, new_cols], axis=1) # 기존데이터 프레임에 새로운 컬럼 추가
df_total.fillna(0, inplace=True) # 첫 행 NaN 제거

# 지역별 데이터 로드
df = pd.read_csv("kr_regional_daily_excel.csv")
# 날짜 형식 변환 및 정렬
df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
df = df.sort_values(["region", "date"]).reset_index(drop=True)
# 지역별 신규확진자수
df["new_confirmed"] = (
    df.groupby("region")["confirmed"].diff().fillna(0).clip(lower=0)
)
# 대구 지역 데이터 필터링
df_Daegu = df[df["region"]=="Daegu"][["date", "new_confirmed"]]


fig = go.Figure()
fig.add_trace(go.Scatter(x=df_total.date, y=df_total.new_confirmed,
                         mode='lines+markers', name='한국 전체 신규 확진자 수',))

fig.add_trace(go.Bar(x=df_Daegu.date, y=df_Daegu.new_confirmed,
                     name = '대구 지역 신규 확진자 수',))

fig.update_layout(
    title = "한국 전체, 대구 일별 신규 확진자수",
    xaxis = dict(
        title = "날짜",
        range = ["2020-02-17","2020-08-31"]
    ),
    yaxis = dict(
        title = "신규 확진자 수",
        range = [0,1000]
    )
)
fig.show()