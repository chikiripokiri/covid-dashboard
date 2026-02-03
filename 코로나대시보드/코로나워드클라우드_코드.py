import pandas as pd
from wordcloud import WordCloud
import plotly.graph_objects as go
import plotly.express as px

file_path = 'kr_regional_daily_excel.csv'
df = pd.read_csv(file_path)

target_date = 20230904
daily_df = df[df['date'] == target_date].copy()

# Translate English regions to Korean
korean_mapping = {
    'Seoul': '서울', 'Busan': '부산', 'Daegu': '대구', 'Incheon': '인천',
    'Gwangju': '광주', 'Daejeon': '대전', 'Ulsan': '울산', 'Sejong': '세종',
    'Gyeonggi': '경기', 'Gangwon': '강원', 'Chungbuk': '충북', 'Chungnam': '충남',
    'Jeonbuk': '전북', 'Jeonnam': '전남', 'Gyeongbuk': '경북', 'Gyeongnam': '경남',
    'Jeju': '제주', 'Quarantine': '검역'
}

# Apply mapping
daily_df['region_kr'] = daily_df['region'].map(korean_mapping)
original_data = daily_df.set_index('region_kr')['confirmed'].to_dict()

def calculate_weight(count):
    if count < 500000:
        return 1
    elif count < 1000000:
        return 2
    elif count < 2000000:
        # Base 3 at 1,000,000
        # (count - 1000000) // 100000 increases index
        increment = int((count - 1000000) // 100000)
        return 3 + increment
    elif count < 5000000:
        return 13
    elif count < 8000000:
        return 14
    else:
        return 15

weighted_data = {k: calculate_weight(v) for k, v in original_data.items()}

# 3. Generate Word Cloud Layout
# Use square canvas to cluster words to center
# Relative scaling 1.0 for strict proportions
# REQUIRED: Korean font path. AppleGothic is standard on Mac.
font_path = '/System/Library/Fonts/Supplemental/AppleGothic.ttf'

import numpy as np
# Create circular mask
x, y = np.ogrid[:600, :600]
# circle center (300, 300), radius 180 (Reduced closer to center)
mask = (x - 300) ** 2 + (y - 300) ** 2 > 180 ** 2
mask = 255 * mask.astype(int)


wc = WordCloud(
    width=600, 
    height=600, 
    background_color='white', 
    max_words=100, 
    relative_scaling=1.0, 
    min_font_size=1,
    font_path=font_path,
    mask=mask
)
wc.generate_from_frequencies(weighted_data)

word_list = []
size_list = []
x_list = []
y_list = []
color_list = []
hover_text_list = []

for item in wc.layout_:
    word = item[0][0] # The word text (now Korean)
    original_count = original_data[word] # Original count
    
    font_size = item[1]
    position = item[2]
    orientation = item[3]
    color = item[4] 
    
    x = position[1] 
    y = position[0] 
    
    word_list.append(word)
    # Scale font size. 
    size_list.append(font_size * 0.5) 
    x_list.append(position[1] + font_size/2) 
    y_list.append(position[0] + font_size/2) 
    
    hover_text_list.append(f"{word}: {original_count:,}")
    color_list.append(original_count) # Color based on original magnitude

if not color_list:
    print("No data found for word cloud.")
    exit()

min_count = min(color_list)
max_count = max(color_list)
norm_color_list = [(c - min_count) / (max_count - min_count) if max_count > min_count else 0.5 for c in color_list]

import plotly.colors as pc

colorscale_name = 'Viridis' 
hex_colors = pc.sample_colorscale(colorscale_name, norm_color_list)

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=x_list,
    y=y_list,
    mode='text',
    text=word_list,
    hovertext=hover_text_list,
    hoverinfo='text',
    textfont=dict(
        size=size_list,
        color=hex_colors,
        family="AppleGothic" # Ensure Plotly also uses a Korean font
    )
))
fig.update_layout(
    width=600,
    height=600,
    xaxis=dict(showgrid=False, showticklabels=False, visible=False),
    yaxis=dict(showgrid=False, showticklabels=False, visible=False, autorange='reversed'), 
    plot_bgcolor='white',
    title=f"Korean COVID-19 Confirmed Cases by Region (as of {target_date})",
    hovermode='closest',
    margin=dict(l=20, r=20, t=40, b=20) # Tight margins
)

output_file = 'korea_covid_wordcloud.html'
fig.write_html(output_file)
print(f"Generated {output_file}")
