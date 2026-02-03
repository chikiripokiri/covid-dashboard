import json
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import rasterio
from rasterio import features, transform
from scipy.ndimage import binary_dilation

# 1. Inputs
geojson_path = 'korea_provinces.json'
csv_path = '../kr_regional_daily_excel.csv'

# 2. Load Data
print("Loading Data...")
with open(geojson_path, 'r', encoding='utf-8') as f:
    sk_geojson = json.load(f)

df = pd.read_csv(csv_path)
df['date'] = df['date'].astype(str)
latest_date = df['date'].max()
print(f"Using COVID data from: {latest_date}")
latest_df = df[df['date'] == latest_date]
covid_data = latest_df.set_index('region')['confirmed'].to_dict()

# Name Mapping
name_map = {
    'Seoul': '서울특별시', 'Busan': '부산광역시', 'Daegu': '대구광역시',
    'Incheon': '인천광역시', 'Gwangju': '광주광역시', 'Daejeon': '대전광역시',
    'Ulsan': '울산광역시', 'Sejong': '세종특별자치시', 'Gyeonggi': '경기도',
    'Gangwon': '강원특별자치도', 'Chungbuk': '충청북도', 'Chungnam': '충청남도',
    'Jeonbuk': '전라북도', 'Jeonnam': '전라남도', 'Gyeongbuk': '경상북도',
    'Gyeongnam': '경상남도', 'Jeju': '제주특별자치도'
}

# 3. Define Grid for Rasterization
width, height = 500, 600
min_lon, min_lat = 124.5, 33.0
max_lon, max_lat = 131.0, 38.9

res_lon = (max_lon - min_lon) / width
res_lat = (max_lat - min_lat) / height
aff_trans = transform.from_origin(min_lon, max_lat, res_lon, res_lat)

# 4. Create Elevation Grid
print("Generating 3D Surface from Data...")
elevation = np.full((height, width), np.nan, dtype=np.float32)

def get_height_level(confirmed_cases):
    """
    User Defined Height Scaling:
    - 0 ~ 500,000: 1
    - 500,000 ~ 1,000,000: 2
    - 1,000,000 ~ 2,500,000: +1 per 100,000 (Levels 3 ~ 17)
    - 2,500,000+: 18 (Capped)
    """
    if confirmed_cases < 500000:
        return 1
    elif confirmed_cases < 1000000:
        return 2
    elif confirmed_cases < 2500000:
        return 3 + int((confirmed_cases - 1000000) // 100000)
    else:
        return 18

def get_largest_polygon(geometry):
    """
    Helped function to keep only the largest polygon from a MultiPolygon.
    Uses coordinate count as a proxy for size.
    """
    if geometry['type'] == 'Polygon':
        return geometry
    elif geometry['type'] == 'MultiPolygon':
        polys = geometry['coordinates']
        if not polys:
            return geometry
        largest_poly_coords = max(polys, key=lambda p: len(p[0]))
        return {
            'type': 'Polygon',
            'coordinates': largest_poly_coords
        }
    return geometry

max_level = 0

for feature in sk_geojson['features']:
    kor_name = feature['properties'].get('CTP_KOR_NM')
    
    # Find case count
    case_count = 0
    for csv_name, map_name in name_map.items():
        if map_name == kor_name:
            if csv_name in covid_data:
                case_count = covid_data[csv_name]
            break
            
    # Calculate Step Level
    level = get_height_level(case_count)
    if level > max_level:
        max_level = level
        
    # Simplify Geometry: Keep only the largest block (island filtering)
    # BUT DO NOT APPLY SHAPELY SIMPLIFICATION (FLATTENING)
    largest_geometry = get_largest_polygon(feature['geometry'])
    
    # Use largest_geometry directly for rasterization
    shapes = [(largest_geometry, 1)]
    mask = features.rasterize(
        shapes=shapes,
        out_shape=(height, width),
        transform=aff_trans,
        fill=0,
        dtype='uint8'
    )
    
    # Update grid where mask is 1
    elevation[mask == 1] = level

print(f"Max Level: {max_level}")

# -------------------------------------------------------------
# Fill Sides (Skirt Logic)
# -------------------------------------------------------------
print("Generating Skirt to fill sides...")
valid_mask = ~np.isnan(elevation)
shoreline_mask = binary_dilation(valid_mask, iterations=1) & ~valid_mask
elevation[shoreline_mask] = 0

# 5. Visualize
print("Rendering Plotly Surface...")

x_coords = np.linspace(min_lon, max_lon, width)
y_coords = np.linspace(max_lat, min_lat, height)

# Color Scale: Pastel Blue (Low) -> Pastel Red (High)
colorscale = [
    [0, "#6bb5ff"],       # Level 0
    [0.277, "#b590b5"],   # Level 5 (Pulling Level 9 color to here)
    [1.0, "#ff6b6b"]      # Level 18
]

fig = go.Figure(data=[go.Surface(
    z=elevation,
    x=x_coords,
    y=y_coords,
    colorscale=colorscale,
    cmin=0,
    cmax=18, 
    contours_z=dict(show=True, usecolormap=True, highlightcolor="white", project_z=True),
    lighting=dict(ambient=0.6, roughness=0.1, diffuse=0.8, fresnel=0.2, specular=0.5) 
)])

fig.update_layout(
    title=f'COVID-19 3D Map Ver2 (No Flattening) - {latest_date}',
    scene={
        "xaxis": {"visible": False}, 
        "yaxis": {"visible": False},
        "zaxis": {"title": "Level (1-18)", "visible": True},
        "aspectmode": "manual",
        "aspectratio": {"x": 1, "y": 1.85, "z": 0.5},
        "camera": {
            "eye": {"x": 1.5, "y": -1.5, "z": 0.8}
        }
    },
    autosize=True,
    margin=dict(l=0, r=0, b=0, t=50)
)

output_file = "korea_covid_surface_ver2.html"
fig.write_html(output_file)
print(f"Saved to {output_file}")
