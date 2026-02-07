# 데일리미션할겸 만들어보는 코로나 히스토그램 시각화 코드
# 지역별로 사망자 + 생존자 합쳐서 확진자로 만들어볼까 
# 주마다 ..?

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
# 기존 전처리는 df였는데 여기서는 df_region으로 변경
df_regoion = pd.read_csv("data/kr_regional_daily_excel.csv") # 지역별 데이터 로드
df_regoion["date"] = pd.to_datetime(df_regoion["date"], format="%Y%m%d") # 날짜 형식 변환 
df_regoion = df_regoion.sort_values(["region", "date"]).reset_index(drop=True) # 지역,날짜순 정렬
df_regoion["new_confirmed"] = (
    df_regoion.groupby("region")["confirmed"].diff().fillna(0).clip(lower=0) # 지역에 따른 일자별 신규확진자 컬럼 만들고 결측치 0으로 채우기
)

print(df_regoion.columns)



# 히스토그램 만들기
# https://plotly.com/python/histograms/ 참고

# df = 