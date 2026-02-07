# -*- coding: utf-8 -*-

import pandas as pd                    # 데이터 분석용 라이브러리 (표 형태 데이터 처리)
import plotly.graph_objects as go      # Plotly 그래프 객체 (고급 차트 생성)
from datetime import datetime          # 날짜/시간 처리용
import numpy as np                     # 수학/통계 계산용
import json                            # JSON 데이터 처리용
import webbrowser                      # 브라우저 제어용
import os                              # 파일 경로 처리용


# CSV 파일 경로 설정
# 주의: 파일이 현재 폴더에 있어야 합니다!
file_path = 'D:/생성 AI 응용 서비스 개발자 양성 과정/AI STUDY/github/kr_regional_daily_excel.csv'

# pd.read_csv(): CSV 파일을 DataFrame(표)으로 읽어오기
# encoding='utf-8-sig': 한글 깨짐 방지
df = pd.read_csv(file_path, encoding='utf-8-sig')


df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
df['date1'] = df['date'].dt.strftime('%Y-%m-%d')

print("✓ 날짜 형식 변환 완료: YYYYMMDD → YYYY-MM-DD")


df['region1'] = df['region'].str.capitalize()

# Quarantine(격리시설) 데이터 제거
# 비교 연산자 !=: '같지 않다'
original_count = len(df)
df = df[df['region1'] != 'Quarantine'].copy()
removed_count = original_count - len(df)

print(f"✓ 지역명 첫 글자 대문자 처리 완료")
print(f"✓ Quarantine 데이터 제거: {removed_count:,}행")


print("\n[3단계] 누락된 날짜 데이터 보정...")

# 데이터 정렬: 지역별, 날짜별로 정렬
# sort_values(): DataFrame 정렬 함수
df = df.sort_values(['region1', 'date']).reset_index(drop=True)

# 전체 날짜 범위 생성
# min(): 최소값, max(): 최대값
min_date = df['date'].min()
max_date = df['date'].max()

# pd.date_range(): 시작일부터 종료일까지 모든 날짜 생성
# freq='D': 일(Day) 단위
date_range = pd.date_range(start=min_date, end=max_date, freq='D')

# 각 지역별로 누락된 날짜 채우기
regions = df['region1'].unique()  # unique(): 중복 제거
filled_data = []  # 빈 리스트 생성 (채워진 데이터 저장용)

# for 반복문: 각 지역마다 아래 작업 반복
for region in regions:
    # 특정 지역 데이터만 필터링
    region_df = df[df['region1'] == region].copy()
    
    # 전체 날짜 범위로 DataFrame 생성
    complete_dates = pd.DataFrame({'date': date_range})
    complete_dates['region1'] = region
    
    # merge(): 두 표를 합치기 (SQL의 JOIN과 유사)
    # how='left': 왼쪽(complete_dates)의 모든 행 유지
    merged = complete_dates.merge(region_df, on=['date', 'region1'], how='left')
    
    # ffill(): Forward Fill - 빈 값을 이전 값으로 채우기
    # fillna(0): 여전히 빈 값이면 0으로 채우기
    merged['confirmed'] = merged['confirmed'].ffill().fillna(0)
    merged['death'] = merged['death'].ffill().fillna(0)
    merged['released'] = merged['released'].ffill().fillna(0)
    merged['date1'] = merged['date'].dt.strftime('%Y-%m-%d')
    
    # 리스트에 추가
    filled_data.append(merged)

# pd.concat(): 여러 DataFrame을 하나로 합치기
# ignore_index=True: 인덱스 번호를 새로 매기기
df = pd.concat(filled_data, ignore_index=True)

print(f"✓ 누락 날짜 보정 완료: {len(df):,}행")

print("\n[4단계] 누적 데이터를 일별 증감으로 변환...")

# groupby(): 그룹별로 묶기 (여기서는 지역별)
# diff(): 현재 행 - 이전 행 계산 (차분)
# fillna(): 첫 행은 이전 행이 없으므로 원본 값 사용
# clip(lower=0): 음수 값을 0으로 제한 (데이터 오류 방지)
# astype(int): 정수형으로 변환

df['confirm1'] = df.groupby('region1')['confirmed'].diff().fillna(df['confirmed']).clip(lower=0).astype(int)
df['death1'] = df.groupby('region1')['death'].diff().fillna(df['death']).clip(lower=0).astype(int)
df['released1'] = df.groupby('region1')['released'].diff().fillna(df['released']).clip(lower=0).astype(int)



# 필요한 컬럼만 선택
output_df = df[['date1', 'region1', 'confirm1', 'death1', 'released1']].copy()

# to_csv(): DataFrame을 CSV 파일로 저장
# index=False: 인덱스 번호는 저장하지 않음
output_df.to_csv('D:/생성 AI 응용 서비스 개발자 양성 과정/AI STUDY/github/kr_covid_temp.txt', index=False)


# 방금 저장한 파일을 다시 읽어오기
data = pd.read_csv('D:/생성 AI 응용 서비스 개발자 양성 과정/AI STUDY/github/kr_covid_temp.txt')

print(f"✓ 파일 읽기 완료: {len(data):,}행")
print(f"\n📊 데이터 통계:")
print(f"  - 기간: {data['date1'].min()} ~ {data['date1'].max()}")
print(f"  - 지역 수: {data['region1'].nunique()}개")
print(f"  - 지역 목록: {', '.join(sorted(data['region1'].unique()))}")
print(f"  - 총 확진자: {data['confirm1'].sum():,}명")
print(f"  - 총 사망자: {data['death1'].sum():,}명")
print(f"  - 총 완치자: {data['released1'].sum():,}명")

print("\n[7단계] 인터랙티브 Bubble Chart 생성...")

data_json = data.to_dict('records')


region_colors = {
    'Seoul': '#EF4444',      # 빨강
    'Busan': '#F59E0B',      # 주황
    'Daegu': '#10B981',      # 초록
    'Incheon': '#3B82F6',    # 파랑
    'Gwangju': '#8B5CF6',    # 보라
    'Daejeon': '#EC4899',    # 핑크
    'Ulsan': '#14B8A6',      # 청록
    'Sejong': '#F97316',     # 진한 주황
    'Gyeonggi': '#6366F1',   # 인디고
    'Gangwon': '#84CC16',    # 라임
    'Chungbuk': '#06B6D4',   # 사이안
    'Chungnam': '#A855F7',   # 보라2
    'Jeonbuk': '#EAB308',    # 노랑
    'Jeonnam': '#22C55E',    # 밝은 초록
    'Gyeongbuk': '#0EA5E9',  # 하늘색
    'Gyeongnam': '#D946EF',  # 마젠타
    'Jeju': '#64748B'        # 슬레이트
}

date_min = data['date1'].min()
date_max = data['date1'].max()

print("✓ 차트 데이터 준비 완료")
print(f"  - 날짜 범위: {date_min} ~ {date_max}")
print(f"  - 전체 데이터 포인트: {len(data):,}개")

# HTML/CSS/JavaScript를 포함한 완전한 웹 페이지 생성
# 이 방식을 사용하면 Plotly 라이브러리 설치 없이도 차트 생성 가능

html_template = '''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>대한민국 코로나19 Bubble Chart</title>
    
    <!-- Plotly.js 라이브러리 로드 (CDN 사용) -->
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    
    <style>
        /* ================================================================
           CSS 스타일: 페이지 디자인 정의
           ================================================================ */
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #ffffff;
        }
        
        /* 차트 컨테이너 */
        #chart {
            width: 100%;
            height: 800px;
        }
        
        /* 정보 박스 */
        .info {
            margin-bottom: 15px;
            padding: 15px;
            background-color: #f9fafb;
            border-radius: 8px;
            font-size: 14px;
            color: #374151;
        }
        
        .info strong {
            color: #111827;
        }
        
        /* 컨트롤 패널 (드롭다운 메뉴) */
        .controls {
            margin-bottom: 20px;
            padding: 15px;
            background-color: #f3f4f6;
            border-radius: 8px;
        }
        
        .controls select {
            padding: 8px 12px;
            margin-right: 15px;
            border: 1px solid #d1d5db;
            border-radius: 6px;
            font-size: 14px;
            background-color: white;
            cursor: pointer;
        }
        
        .controls label {
            margin-right: 8px;
            font-weight: 500;
            color: #374151;
        }
        
        /* ================================================================
           6-(6) region1별 버튼 생성: 지역 선택 패널 스타일
           ================================================================ */
        .region-selector {
            margin-bottom: 20px;
            padding: 15px;
            background-color: #f9fafb;
            border-radius: 8px;
            border: 1px solid #e5e7eb;
        }
        
        .region-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }
        
        .region-buttons {
            display: flex;
            gap: 8px;
        }
        
        /* 전체선택/전체해제 버튼 스타일 */
        .select-btn {
            padding: 6px 12px;
            background-color: white;
            border: 1px solid #d1d5db;
            border-radius: 6px;
            cursor: pointer;
            font-size: 13px;
            transition: all 0.2s;
        }
        
        .select-btn:hover {
            background-color: #f3f4f6;
            border-color: #9ca3af;
        }
        
        /* "확인" 버튼 스타일 */
        .apply-btn {
            padding: 6px 16px;
            background-color: #3b82f6;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 13px;
            font-weight: 500;
            transition: all 0.2s;
        }
        
        .apply-btn:hover {
            background-color: #2563eb;
            transform: scale(1.02);
        }
        
        /* region1별 체크박스 컨테이너 */
        .checkbox-container {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
            gap: 8px;
            max-height: 120px;
            overflow-y: auto;
        }
        
        /* 개별 체크박스 아이템 */
        .checkbox-item {
            display: flex;
            align-items: center;
            padding: 4px;
        }
        
        .checkbox-item input[type="checkbox"] {
            margin-right: 6px;
            cursor: pointer;
            width: 16px;
            height: 16px;
        }
        
        .checkbox-item label {
            cursor: pointer;
            font-size: 13px;
            margin: 0;
            user-select: none;
        }
    </style>
</head>
<body>
    <!-- 데이터 정보 표시 -->
    <div class="info">
        <strong>📊 대한민국 코로나19 데이터 분석</strong><br>
        기간: {date_min} ~ {date_max} | 
        지역(region1): {region_count}개 | 
        총 확진자: {total_confirm:,}명 | 
        총 사망자: {total_death:,}명 | 
        총 완치자: {total_released:,}명
    </div>
    
    <!--  드롭다운 메뉴 1: 확진자/사망자/완치자 선택 -->
    <!--  드롭다운 메뉴 2: 일별/주간/월간/분기 선택 -->
    <div class="controls">
        <label for="metricSelect">📈 데이터 선택:</label>
        <select id="metricSelect">
            <option value="confirm1">확진자</option>
            <option value="death1">사망자</option>
            <option value="released1">완치자</option>
        </select>
        
        <label for="periodSelect">📅 기간 선택:</label>
        <select id="periodSelect">
            <option value="daily">일별</option>
            <option value="weekly">주간</option>
            <option value="monthly">월간</option>
            <option value="quarterly">분기</option>
        </select>
    </div>
    
    <!-- ================================================================
         - region1별 체크박스
         - 전체선택/전체해제 버튼
         - "확인" 버튼
         ================================================================ -->
    <div class="region-selector">
        <div class="region-header">
            <strong>📍 지역 선택 (region1)</strong>
            <div class="region-buttons">
                <!-- 전체선택 버튼 -->
                <button id="selectAllBtn" class="select-btn">✓ 전체 선택</button>
                <!-- 전체해제 버튼 -->
                <button id="deselectAllBtn" class="select-btn">✗ 전체 해제</button>
                <!-- "확인" 버튼: Y축을 선택된 region1에 맞춰 영역 분할 및 Bubble 최적화 -->
                <button id="applyRegionBtn" class="apply-btn">✓ 확인</button>
            </div>
        </div>
        <!-- region1별 체크박스가 동적으로 생성될 컨테이너 -->
        <div id="regionCheckboxes" class="checkbox-container"></div>
    </div>
    
    <!-- Plotly 차트가 렌더링될 컨테이너 -->
    <div id="chart"></div>

    <script>
        /*
         * ====================================================================
         * JavaScript 코드: 차트 생성 및 인터랙션 처리
         * ====================================================================
         * 이 코드는 Python의 데이터를 받아서 브라우저에서 동적으로 차트를 생성합니다.
         */
        
        // Python에서 전달받은 데이터 (JSON 형식)
        const rawData = {data_json};
        
        // 6-(7) region1별 색상 정의
        const regionColors = {region_colors_json}; //여기수정

        // 메트릭 이름 매핑 (confirm1 → 확진자)
        const metricNames = {{
            'confirm1': '확진자',
            'death1': '사망자',
            'released1': '완치자'
        }};
        
        /**
         * ================================================================
         * 기간별 데이터 집계 함수
         * ================================================================
         * 
         * @param {{Array}} data - 원본 데이터 배열
         * @param {{string}} period - 집계 기간 (daily/weekly/monthly/quarterly)
         * @returns {{Array}} 집계된 데이터 배열
         * 
         * 역할: 일별 데이터를 주간/월간/분기별로 합산
         */
        function aggregateData(data, period) {{
            // 일별은 집계하지 않고 그대로 반환
            if (period === 'daily') {{
                return data;
            }}
            
            // 집계 결과를 저장할 객체
            // 키(key): "지역_날짜", 값(value): 집계된 데이터
            const aggregated = {{}};
            
            // 각 데이터 행을 순회하며 집계
            data.forEach(row => {{
                const date = new Date(row.date1);
                let key;  // 집계 키를 저장할 변수
                
                if (period === 'weekly') {{
                    // 주간 집계: 일요일을 기준으로 주의 시작일 계산
                    const dayOfWeek = date.getDay();  // 0(일) ~ 6(토)
                    const weekStart = new Date(date);
                    weekStart.setDate(date.getDate() - dayOfWeek);
                    const weekKey = weekStart.toISOString().split('T')[0];
                    key = `${{row.region1}}_${{weekKey}}`;
                }} else if (period === 'monthly') {{
                    // 월간 집계: 매월 1일 기준
                    const monthKey = `${{date.getFullYear()}}-${{String(date.getMonth() + 1).padStart(2, '0')}}-01`;
                    key = `${{row.region1}}_${{monthKey}}`;
                }} else if (period === 'quarterly') {{
                    // 분기별 집계: Q1(1월), Q2(4월), Q3(7월), Q4(10월)
                    const year = date.getFullYear();
                    const month = date.getMonth();  // 0~11
                    const quarter = Math.floor(month / 3);  // 0,1,2,3
                    const quarterMonth = (quarter * 3) + 1;  // 1,4,7,10
                    const quarterKey = `${{year}}-${{String(quarterMonth).padStart(2, '0')}}-01`;
                    key = `${{row.region1}}_${{quarterKey}}`;
                }}
                
                // 키가 처음 등장하면 새로운 집계 데이터 생성
                if (!aggregated[key]) {{
                    aggregated[key] = {{
                        date1: key.split('_')[1],
                        region1: row.region1,
                        confirm1: 0,
                        death1: 0,
                        released1: 0
                    }};
                }}
                
                // 값 누적 (같은 기간의 데이터를 합산)
                aggregated[key].confirm1 += row.confirm1 || 0;
                aggregated[key].death1 += row.death1 || 0;
                aggregated[key].released1 += row.released1 || 0;
            }});
            
            // 객체를 배열로 변환하여 반환
            return Object.values(aggregated);
        }}
        
        /**
         * ================================================================
         * Plotly 트레이스 생성 함수
         * ================================================================
         * 
         * @param {{Array}} data - 데이터 배열
         * @param {{string}} metric - 메트릭 ('confirm1', 'death1', 'released1')
         * @param {{Array}} selectedRegions - 선택된 region1 배열
         * @returns {{Array}} Plotly 트레이스 배열
         * 
         * 역할: region1별로 버블 차트 데이터 생성
         */
        function createTraces(data, metric, selectedRegions) {{
            // 6-(6) 선택된 region1만 사용
            // 선택된 것이 없으면 전체 region1 사용
            const regions = selectedRegions.length > 0 
                ? selectedRegions 
                : [...new Set(data.map(d => d.region1))].sort();
           
            const globalData = data.filter(d =>
                regions.includes(d.region1) && d[metric] > 0
            );
            const globalValues = globalData.map(d => d[metric]);
            const globalMaxValue = Math.max(...globalValues, 1);
            const globalMinValue = Math.min(...globalValues.filter(v => v > 0), 1);

            return regions.map(region => {{
                // Y축: 특정 region1 데이터만 필터링
                const regionData = data.filter(d => d.region1 === region);
                
                // 값이 0인 데이터는 표시하지 않음
                const filteredData = regionData.filter(d => d[metric] > 0);
                
                // 데이터가 없으면 null 반환 (나중에 제거됨)
                if (filteredData.length === 0) {{
                    return null;
                }}
                
  
                //버블 크기 최적화(전역 스케일): region 무관하게 global min/max 사용
                const values = filteredData.map(d => d[metric]);

                //sqrt 스케일 적용
                // sqrt를 사용하는 이유: 버블의 면적이 값에 비례하도록 함
                const sizes = values.map(value => {{
                    // 정규화: 0~1 범위로 변환
 
                    const normalizedValue = (value - globalMinValue) / (globalMaxValue - globalMinValue || 1);
                
                    // sqrt 스케일: 제곱근 적용
                    const sqrtScale = Math.sqrt(normalizedValue);
                    // 크기 범위: 10~50 (버블이 너무 작거나 크지 않도록)
                    return 10 + (sqrtScale * 40);
                }});
                
                // Plotly Scatter 트레이스 객체 생성
                return {{
                    // X축: 날짜 (date1)
                    x: filteredData.map(d => d.date1),
                    
                    // Y축: 지역 (region1)
                    y: filteredData.map(d => d.region1),
                    
                    mode: 'markers',  // 점(마커)만 표시
                    
                    // 범례: region1 이름 표시
                    name: region,
                    
                    // 버블 스타일 정의
                    marker: {{
                        size: sizes,  // 계산된 버블 크기 배열
                        // region1별로 각각 지정된 색상
                        color: regionColors[region] || '#94A3B8',
                        opacity: 0.7,  // 투명도 70%
                        line: {{
                            color: 'white',  // 버블 테두리 색상
                            width: 1  // 테두리 두께
                        }}
                    }},
                    
                    // customdata: 실제 값 저장 (sqrt 스케일 적용 전)
                    // hover에서 원본 값을 표시하기 위해 사용
                    customdata: filteredData.map(d => [
                        d.date1,    // 날짜
                        d.region1,  // 지역
                        d[metric]   // 실제 값
                    ]),
                    
                    // Hover 템플릿: 마우스를 올렸을 때 표시될 내용
                    hovertemplate: 
                        '%{{customdata[0]}}<br>' +  // X축: 날짜
                        '%{{customdata[1]}}: %{{customdata[2]:,}}명<br>' +  // Y축: region1, 값
                        '<extra></extra>',  // 추가 정보 숨김
                    
                    type: 'scatter'  // 차트 타입
                }};
            }}).filter(trace => trace !== null);  // null 제거
        }}
        
        /**
         * ================================================================
         * 차트 업데이트 함수
         * ================================================================
         * 
         * 역할: "확인" 버튼 클릭 시 실행되어 선택된 region1으로 차트 재생성
         *       Y축을 선택된 region1에 맞춰 영역 분할
         */
        function updateChart() {{
            // 현재 선택된 메트릭과 기간 가져오기
            const metric = document.getElementById('metricSelect').value;
            const period = document.getElementById('periodSelect').value;
            
            // 체크된 region1 가져오기
            const selectedRegions = Array.from(
                document.querySelectorAll('.checkbox-item input:checked')
            ).map(cb => cb.value);
            
            console.log('선택된 region1:', selectedRegions);  // 디버깅용
            
            // 기간별 데이터 집계
            const processedData = aggregateData(rawData, period);
            
            // 트레이스 생성 시 선택된 region1 전달
            const traces = createTraces(processedData, metric, selectedRegions);
            
            // ============================================================
            // Plotly 레이아웃 설정: 차트의 외형과 스타일 정의
            // ============================================================
            const layout = {{
                // 그래프 제목 (안쪽 배치)
                title: {{
                    text: '대한민국 코로나19',
                    x: 0.5,          // 제목 위치 (0.5 = 중앙)
                    y: 0.95,         // 세로 위치 (0.95 = 상단)
                    xanchor: 'center',
                    yanchor: 'top',
                    font: {{
                        size: 24,
                        color: '#111827'
                    }}
                }},
                
                // X축 설정
                xaxis: {{
                    title: '',
                    type: 'date',  // 날짜 타입
                    // 6-(10) X축 표시: 일자까지만 (시간 표시 제거)
                    tickformat: '%Y-%m-%d',
                    hoverformat: '%Y-%m-%d',
                    // 6-(16) X축 MIN/MAX 설정
                    range: ['{date_min}', '{date_max}'],
                    // 6-(11) 격자선 색상
                    gridcolor: '#F3F4F6',
                    showgrid: true,
                    zeroline: false,
                    
                    // 6-(14) 슬라이더 추가
                    rangeslider: {{
                        visible: true,
                        // 6-(15) 슬라이더 배경: 하얀색
                        bgcolor: 'white',
                        thickness: 0.05,
                        bordercolor: '#d1d5db',
                        borderwidth: 1
                    }}
                }},
                
                //Y축 설정
                yaxis: {{
                    title: '',
                    type: 'category',  // 카테고리 타입
                    // 6-(6) Y축을 선택된 region1에 맞춰 영역 분할
                    // categoryorder: 배열 순서대로 표시
                    // categoryarray: 표시할 카테고리 배열
                    categoryorder: 'array',
                    categoryarray: selectedRegions.length > 0 
                        ? selectedRegions.sort()  // 선택된 region1만
                        : [...new Set(rawData.map(d => d.region1))].sort(),  // 전체
                    // 6-(11) 격자선 색상
                    gridcolor: '#F3F4F6',
                    showgrid: true,
                    zeroline: false,
                    fixedrange: false
                }},
                
                // 배경색 없음 (투명)
                plot_bgcolor: 'rgba(0,0,0,0)',
                paper_bgcolor: 'rgba(0,0,0,0)',
                
                // Hover 모드: 가장 가까운 점 정보 표시
                hovermode: 'closest',
                
                // 범례 설정
                showlegend: true,
                legend: {{
                    orientation: 'v',  // 세로 방향
                    x: 1.02,  // 차트 오른쪽
                    y: 1,
                    xanchor: 'left',
                    yanchor: 'top',
                    bgcolor: 'rgba(255,255,255,0.9)',
                    bordercolor: '#E5E7EB',
                    borderwidth: 1,
                    font: {{ size: 10 }}
                }},
                
                height: 800,
                margin: {{ l: 80, r: 180, t: 100, b: 120 }}
            }};
            
            // 모드바 설정 (확대/축소/저장 등 도구)
            const config = {{
                displayModeBar: true,  // 모드바 표시
                displaylogo: false,  // Plotly 로고 숨김
                toImageButtonOptions: {{
                    format: 'png',
                    filename: 'korea_covid19',
                    height: 1000,
                    width: 1600,
                    scale: 2
                }}
            }};
            
            // Plotly 차트 렌더링
            // newPlot: 새로운 차트 생성 또는 기존 차트 대체
            Plotly.newPlot('chart', traces, layout, config);
        }}
        
        /**
         * ================================================================
         * region1별 체크박스 초기화 함수
         * ================================================================
         * 
         * 역할: 데이터에서 region1 목록을 가져와 체크박스 동적 생성
         */
        function initializeRegionCheckboxes() {{
            // region1 목록 추출 (중복 제거 후 정렬)
            const regions = [...new Set(rawData.map(d => d.region1))].sort();
            const container = document.getElementById('regionCheckboxes');
            
            // 각 region1별로 체크박스 생성
            regions.forEach(region => {{
                // div 엘리먼트 생성
                const item = document.createElement('div');
                item.className = 'checkbox-item';
                
                // 체크박스 생성
                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.id = `region_${{region}}`;
                checkbox.value = region;
                checkbox.checked = true;  // 기본적으로 모두 선택됨
                
                // 라벨 생성
                const label = document.createElement('label');
                label.htmlFor = `region_${{region}}`;
                label.textContent = region;
                
                // 엘리먼트 조립
                item.appendChild(checkbox);
                item.appendChild(label);
                container.appendChild(item);
            }});
        }}
        
        // ====================================================================
        // 페이지 로드 시 초기화 및 이벤트 리스너 등록
        // ====================================================================
        
        // region1별 체크박스 생성
        initializeRegionCheckboxes();
        
        // 초기 차트 렌더링
        updateChart();
        
        // 드롭다운 메뉴 변경 시 자동 업데이트
        document.getElementById('metricSelect').addEventListener('change', updateChart);
        document.getElementById('periodSelect').addEventListener('change', updateChart);
        
        // 전체선택 버튼 클릭 이벤트
        document.getElementById('selectAllBtn').addEventListener('click', () => {{
            document.querySelectorAll('.checkbox-item input').forEach(cb => {{
                cb.checked = true;
            }});
        }});
        
        // 전체해제 버튼 클릭 이벤트
        document.getElementById('deselectAllBtn').addEventListener('click', () => {{
            document.querySelectorAll('.checkbox-item input').forEach(cb => {{
                cb.checked = false;
            }});
        }});
        
        // "확인" 버튼 클릭 이벤트
        // Y축을 선택된 region1에 맞춰 영역 분할 및 Bubble 크기 최적화
        document.getElementById('applyRegionBtn').addEventListener('click', () => {{
            updateChart();  // 차트 재생성
        }});
    </script>
</body>
</html>'''
##KeyError: '\n            font-family' --> 첫번째 컴파일에서 에러 이곳을 추가함---2차시도
# ==========================================================
# str.format() 중괄호 충돌 해결(자동 이스케이프)
# - CSS/JS의 { } 는 format이 변수로 착각 → KeyError 발생
# - 치환해야 하는 자리({date_min} 같은 것)만 "임시 토큰"으로 보호한 뒤
#   나머지 { } 를 전부 {{ }} 로 바꿔줍니다.
# ==========================================================

placeholders = {
    "{data_json}": "__DATA_JSON__",
    "{region_colors_json}": "__REGION_COLORS__",
    "{date_min}": "__DATE_MIN__",
    "{date_max}": "__DATE_MAX__",
    "{region_count}": "__REGION_COUNT__",
    "{total_confirm:,}": "__TOTAL_CONFIRM__",
    "{total_death:,}": "__TOTAL_DEATH__",
    "{total_released:,}": "__TOTAL_RELEASED__",
}

# 1) 치환할 자리만 토큰으로 잠시 보호
for k, token in placeholders.items():
    html_template = html_template.replace(k, token)

# 2) 나머지 모든 중괄호를 format-safe하게 이스케이프
html_template = html_template.replace("{", "{{").replace("}", "}}")

# 3) 보호했던 토큰을 다시 원래 치환 자리로 복원
for k, token in placeholders.items():
    html_template = html_template.replace(token, k)
#-------------------------------------------------------------------------2차시도
# HTML 파일 생성
html_content = html_template.format(
    data_json=json.dumps(data_json),
    region_colors_json=json.dumps(region_colors),
    date_min=date_min,
    date_max=date_max,
    region_count=data['region1'].nunique(),
    total_confirm=int(data['confirm1'].sum()),
    total_death=int(data['death1'].sum()),
    total_released=int(data['released1'].sum())
)

# ✅ [최소 수정] JS 문법 오류(Unexpected token '{') 해결:
# 템플릿 내부에 남은 '{{' '}}'를 '{' '}'로 평탄화하여 자바스크립트 파싱 오류를 방지합니다.
html_content = html_content.replace('{{', '{').replace('}}', '}')

# HTML 파일 저장
output_html = 'korea_covid19_interactive.html'
with open(output_html, 'w', encoding='utf-8') as f:
    f.write(html_content)

print("✓ HTML 파일 생성 완료!")
print(f"  - 파일명: {output_html}")

# ==============================================================================
# 브라우저에서 차트 표시
# ==============================================================================
print("\n[8단계] 브라우저에서 차트 표시...")

# 현재 파일의 절대 경로 생성
file_path = os.path.abspath(output_html)

# 10. VSCode에서 바로 실행해서 볼 수 있도록 처리
# webbrowser.open(): 기본 브라우저에서 HTML 파일 열기
webbrowser.open('file://' + file_path)

