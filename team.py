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
fig = px.line(df_total, x="date", y="new_confirmed",
              title="한국 전체 일별 신규 확진자수",
              labels={"date":"날짜", "new_confirmed":"신규 확진자 수"},
              log_y=True,) # y축 로그스케일
# 대구 지역 신규 확진자수 시각화
fig.add_trace(go.Scatter(x=df_Daegu.date, y=df_Daegu.new_confirmed,
                         mode='lines', name='대구 지역 신규 확진자 수')) 
fig.show()




# 처음 날짜부터 4월 10일 정도까지의 대구에서 시작된 1차 대유행 날짜에 따른 지도상 히트맵 구현 =>