import pandas as pd
from wordcloud import WordCloud
import plotly.graph_objects as go
import plotly.express as px

# 1. Load Data
file_path = 'kr_regional_daily_excel.csv'
df = pd.read_csv(file_path)

# 2. Filter for the latest date (20230904)
#   The file has 'date', 'region', 'confirmed', 'death', 'released'
#   We need cumulative confirmed cases for each region on the last date.
target_date = 20230904
daily_df = df[df['date'] == target_date].copy()

# Remove 'Quarantine' or 'Total' if present, usually 'Quarantine' is a separate category
# Let's keep all regions except maybe 'Total' if it exists. Based on previous `tail`, 'Quarantine' exists.
# User asked for regional data, 'Quarantine' (검역) is technically a category. Let's keep it or remove it?
# Usually maps exclude it, but word clouds can include it. I'll include it for now.
# However, let's normalize the region names if needed. They seem to be in English.

# Create a dictionary for word cloud: {region: confirmed_count}
data = daily_df.set_index('region')['confirmed'].to_dict()

# 3. Generate Word Cloud Layout
# We use WordCloud to calculate the positions and sizes of the words.
# We don't actually need the image, just the layout.
# but we need a font for Korean if there were Korean characters.
# The CSV has English region names (Seoul, Busan, etc.), so default font is fine.
# Wait, let's check if the CSV has English or Korean from the `head` output.
# Output of head: "20200217,Seoul,14,0,3" -> English.
# So we don't strictly need a Korean font, but using one doesn't hurt.
# Let's stick to default compatible font or just let WordCloud handle it since it's English.

wc = WordCloud(width=800, height=600, background_color='white', max_words=100)
wc.generate_from_frequencies(data)

# 4. Extract Layout Data for Plotly
# wc.layout_ contains a list of tuples: (word, count), font_size, position, orientation, color
# position is (y, x) ? No, it's (x, y) relative to canvas.
# Actually, let's inspect what wc.layout_ gives.
# It is a list of (string, size, (x, y), orientation, color)

word_list = []
size_list = []
x_list = []
y_list = []
color_list = []
hover_text_list = []

for item in wc.layout_:
    word = item[0][0] # The word text
    count = data[word] # Original count
    font_size = item[1]
    position = item[2]
    orientation = item[3]
    color = item[4] # This is a color string/tuple from WordCloud
    
    # Plotly Scatter text needs x, y.
    # WordCloud 0,0 is top-left. Plotly 0,0 is usually bottom-left unless we reverse y-axis.
    # Let's just use x, y and flip y axis in layout.
    
    x = position[1] # column ?
    y = position[0] # row ? 
    
    word_list.append(word)
    size_list.append(font_size)
    x_list.append(position[1] + font_size/2) # Centering attempt
    y_list.append(position[0] + font_size/2) 
    
    hover_text_list.append(f"{word}: {count:,}")
    color_list.append(count)

# Map counts to colors using a colormap
# We need to normalize the counts to 0-1 range for colormap
if not color_list:
    print("No data found for word cloud.")
    exit()

min_count = min(color_list)
max_count = max(color_list)
norm_color_list = [(c - min_count) / (max_count - min_count) if max_count > min_count else 0.5 for c in color_list]

# Use Plotly's built-in colorscale sampling or matplotlib
import plotly.colors as pc

# Viridis colorscale
colorscale_name = 'Viridis' 
# pc.sample_colorscale takes a list of normalized values [0-1] and returns hex colors
hex_colors = pc.sample_colorscale(colorscale_name, norm_color_list)

# 5. Create Plotly Figure
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
        color=hex_colors
    )
))

# Update layout to match WordCloud dimensions and hide axes
fig.update_layout(
    width=800,
    height=600,
    xaxis=dict(showgrid=False, showticklabels=False, visible=False),
    yaxis=dict(showgrid=False, showticklabels=False, visible=False, autorange='reversed'), 
    plot_bgcolor='white',
    title=f"Korean COVID-19 Confirmed Cases by Region (as of {target_date})",
    hovermode='closest'
)

output_file = 'korea_covid_wordcloud.html'
fig.write_html(output_file)
print(f"Generated {output_file}")
