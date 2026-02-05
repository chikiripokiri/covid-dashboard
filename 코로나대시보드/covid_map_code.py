import json
import argparse
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from rasterio import features, transform
from scipy.ndimage import binary_dilation

# ---------------------------------------------------------
# 1. Configuration & Constants
# ---------------------------------------------------------
WIDTH, HEIGHT = 500, 600
MIN_LON, MIN_LAT = 124.5, 33.0
MAX_LON, MAX_LAT = 131.0, 38.9
GRID_SHAPE = (HEIGHT, WIDTH)

RES_LON = (MAX_LON - MIN_LON) / WIDTH
RES_LAT = (MAX_LAT - MIN_LAT) / HEIGHT
AFF_TRANS = transform.from_origin(MIN_LON, MAX_LAT, RES_LON, RES_LAT)

# ---------------------------------------------------------
# 2. Helpers
# ---------------------------------------------------------
def get_largest_polygon(geometry):
    """
    Keep only the largest polygon from a MultiPolygon (island filtering).
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

# ---------------------------------------------------------
# 3. Data Processing
# ---------------------------------------------------------
def load_data(csv_path, geojson_path):
    print("Loading Data...")
    
    # Load GeoJSON
    with open(geojson_path, 'r', encoding='utf-8') as f:
        geojson = json.load(f)
    geojson_str = json.dumps(geojson) # For embedding in JS if needed

    # Load CSV
    df = pd.read_csv(csv_path)
    # Ensure necessary columns
    required_cols = {"date", "region", "death", "confirmed"}
    if not required_cols.issubset(df.columns):
        pass

    df['date'] = df['date'].astype(str)
    
    return df, geojson, geojson_str

def process_names_and_dates(df, geojson):
    # Extract canonical names from GeoJSON (ordering matters for the mask)
    regions_order = [f["properties"]["CTP_ENG_NM"] for f in geojson["features"]]
    
    # Region Alias Map
    region_alias = {
        "Seoul": "Seoul", "Busan": "Busan", "Daegu": "Daegu", "Incheon": "Incheon",
        "Gwangju": "Gwangju", "Daejeon": "Daejeon", "Ulsan": "Ulsan", "Sejong": "Sejong-si",
        "Sejong-si": "Sejong-si", "Gyeonggi": "Gyeonggi-do", "Gangwon": "Gangwon-do",
        "Chungbuk": "Chungcheongbuk-do", "Chungnam": "Chungcheongnam-do",
        "Jeonbuk": "Jeollabuk-do", "Jeonnam": "Jellanam-do",
        "Gyeongbuk": "Gyeongsangbuk-do", "Gyeongnam": "Gyeongsangnam-do",
        "Jeju": "Jeju-do",
        "서울": "Seoul", "부산": "Busan", "대구": "Daegu", "인천": "Incheon",
        "광주": "Gwangju", "대전": "Daejeon", "울산": "Ulsan", "세종": "Sejong-si",
        "세종특별자치시": "Sejong-si", "경기": "Gyeonggi-do", "경기도": "Gyeonggi-do",
        "강원": "Gangwon-do", "강원도": "Gangwon-do", "강원특별자치도": "Gangwon-do",
        "충북": "Chungcheongbuk-do", "충청북도": "Chungcheongbuk-do",
        "충남": "Chungcheongnam-do", "충청남도": "Chungcheongnam-do",
        "전북": "Jeollabuk-do", "전라북도": "Jeollabuk-do",
        "전남": "Jellanam-do", "전라남도": "Jellanam-do",
        "경북": "Gyeongsangbuk-do", "경상북도": "Gyeongsangbuk-do",
        "경남": "Gyeongsangnam-do", "경상남도": "Gyeongsangnam-do",
        "제주": "Jeju-do", "제주도": "Jeju-do", "제주특별자치도": "Jeju-do"
    }

    # Group by date
    date_groups_levels = {}
    date_groups_raw = {}
    
    dates_sorted = sorted(df['date'].unique())
    print("Processing daily data...")
    
    MAX_LEVEL = 15
    CAP_CONFIRMED = 2500000
    
    for date in dates_sorted:
        day_df = df[df['date'] == date]
        
        # 1. Aggregate Raw Counts
        conf_map = {r: 0 for r in regions_order}
        for _, row in day_df.iterrows():
            reg_raw = str(row['region'])
            reg = region_alias.get(reg_raw, reg_raw)
            if reg not in conf_map:
                if f"{reg}-do" in conf_map: reg = f"{reg}-do"
                elif f"{reg}-si" in conf_map: reg = f"{reg}-si"
            
            if reg in conf_map:
                conf_map[reg] += int(row.get('confirmed', 0))
        
        raw_vals = [conf_map[r] for r in regions_order]
        
        # 2. Calculate Levels (Dynamic Relative Scaling)
        day_max = max(raw_vals) if raw_vals else 0
        reference_val = min(day_max, CAP_CONFIRMED)
        
        level_vals = []
        for val in raw_vals:
            if reference_val == 0:
                lvl = 0
            else:
                ratio = val / reference_val
                lvl = int(ratio * MAX_LEVEL)
                
                # Boundaries
                if lvl < 1 and val > 0: lvl = 1
                if lvl > MAX_LEVEL: lvl = MAX_LEVEL
            
            level_vals.append(lvl)
        
        date_groups_raw[date] = raw_vals
        date_groups_levels[date] = level_vals

    return regions_order, dates_sorted, date_groups_levels, date_groups_raw

def generate_base_grid(geojson, regions_order):
    print("Generating 3D Base Grid...")
    grid = np.full(GRID_SHAPE, -1, dtype=np.int32)
    
    for idx, region_name in enumerate(regions_order):
        feature = next(f for f in geojson['features'] if f['properties']['CTP_ENG_NM'] == region_name)
        geom = get_largest_polygon(feature['geometry'])
        mask = features.rasterize(
            [(geom, 1)],
            out_shape=GRID_SHAPE,
            transform=AFF_TRANS,
            fill=0,
            dtype='uint8'
        )
        grid[mask == 1] = idx

    valid_mask = grid >= 0
    shoreline_mask = binary_dilation(valid_mask, iterations=1) & ~valid_mask
    grid[shoreline_mask] = -2
    
    return grid

# ---------------------------------------------------------
# 4. HTML Generation
# ---------------------------------------------------------
def generate_html(output_path, regions_order, dates, levels_data, raw_data, base_grid, geojson, geojson_str):
    print("Generating HTML...")
    base_grid_flat = base_grid.flatten()
    init_date = dates[-1]
    
    CAP_NUM = 2500000
    
    # --- Python-side Initial Data Construction ---
    
    # X, Y Coords
    x_coords = np.linspace(MIN_LON, MAX_LON, WIDTH)
    y_coords = np.linspace(MAX_LAT, MIN_LAT, HEIGHT)
    
    # 1. Build Initial 3D Surface Data (Python equivalent of JS build3DSurface)
    levels = np.array(levels_data[init_date])
    # Create Z matrix initialized with NaNs
    z_matrix = np.full(base_grid.shape, np.nan)
    
    # -2 is sea/boundary (0 height), >=0 is region index (get level)
    # Using vectorized operations for speed
    mask_region = base_grid >= 0
    mask_sea = base_grid == -2
    
    z_matrix[mask_sea] = 0
    z_matrix[mask_region] = levels[base_grid[mask_region]]
    
    # Plotly expects list of lists for Surface Z
    z_list = z_matrix.tolist()
    
    trace3d = {
        "type": "surface",
        "z": z_list,
        "x": x_coords.tolist(),
        "y": y_coords.tolist(),
        "colorscale": [
            [0, "#6bb5ff"],
            [0.4, "#b590b5"],
            [1.0, "#ff6b6b"]
        ],
        "cmin": 0, "cmax": 15,
        "showscale": False,
        "contours": {"z": {"show": False, "project": {"z": True}}},
        "lighting": {"ambient": 0.6, "roughness": 0.1, "diffuse": 0.8, "fresnel": 0.2, "specular": 0.5},
        "visible": True,
        "name": "3D"
    }

    # 2. Build Initial 2D Choropleth Data
    raw_vals = raw_data[init_date]
    day_max = max(raw_vals) if raw_vals else 0
    view_max = min(day_max, CAP_NUM) if day_max > CAP_NUM else (day_max if day_max > 0 else 1)
    text_list = [f"{r}: {v}" for r, v in zip(regions_order, raw_vals)]
    
    trace2d = {
        "type": "choropleth",
        "locations": regions_order,
        "z": raw_vals,
        "geojson": geojson,
        "featureidkey": "properties.CTP_ENG_NM",
        "colorscale": "Reds",
        "zmin": 0, "zmax": view_max,
        "text": text_list,
        "hovertemplate": "%{text}<extra></extra>",
        "visible": False,
        "name": "2D"
    }
    
    initial_data = [trace3d, trace2d]

    # --- Python-side Layout Configuration ---
    
    # Update Menus (Buttons)
    updatemenus = [
        {
            "type": "buttons",
            "direction": "left",
            "pad": {"r": 10, "t": 10},
            "showactive": True,
            "x": 0, "y": 1.1, "xanchor": "left", "yanchor": "top",
            "buttons": [
                {
                    "label": "3D Confirmed",
                    "method": "update",
                    "args": [{"visible": [True, False]}, {"scene.visible": True, "geo.visible": False}]
                },
                {
                    "label": "2D Confirmed",
                    "method": "update",
                    "args": [{"visible": [False, True]}, {"scene.visible": False, "geo.visible": True}]
                }
            ]
        }
    ]
    
    # Sliders
    steps = [
        {
            "label": d,
            "method": "skip", # Hijack in JS
            "args": [],
            "execute": False
        }
        for d in dates
    ]
    
    sliders = [
        {
            "active": len(dates) - 1,
            "currentvalue": {"prefix": "Date: "},
            "pad": {"t": 50},
            "len": 0.6,
            "x": 0.2,
            "steps": steps
        }
    ]
    
    layout = {
        "title": f"COVID-19 Confirmed Cases - {init_date}",
        "autosize": True,
        "margin": {"l": 0, "r": 0, "b": 0, "t": 50},
        "scene": { # 3D Scene
            "xaxis": {"visible": False},
            "yaxis": {"visible": False},
            "zaxis": {"title": "Level", "visible": False},
            "aspectmode": "manual",
            "aspectratio": {"x": 1, "y": 1.85, "z": 0.5},
            "camera": {"eye": {"x": 1.5, "y": -1.5, "z": 0.8}}
        },
        "geo": { # 2D Geo
            "fitbounds": "locations", 
            "visible": False,
            "projection": {"type": "mercator"} # Kept as requested
        },
        "coloraxis": { 
            "cmin": 0,
            "colorbar": {"len": 0.8, "title": "Cases"} 
        },
        "updatemenus": updatemenus,
        "sliders": sliders
    }

    # Serialize to JSON for Injection
    initial_data_json = json.dumps(initial_data)
    layout_json = json.dumps(layout)
    base_grid_flat_json = json.dumps(base_grid_flat.tolist()) # Flattened list for JS Array
    
    html_content = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>Integrated COVID-19 Dashboard</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        * {{ box-sizing: border-box; }}
        body {{ 
            font-family: 'Noto Sans KR', Arial, sans-serif; 
            margin: 0; padding: 0; 
            background: #f4f4f9; 
            height: 100vh; 
            display: flex; 
            flex-direction: column; 
            align-items: center; 
            overflow: hidden; 
        }}
        #plot-container {{ 
            width: 100%; 
            height: 100%;
            position: relative;
        }}
        #loading {{ 
            position: absolute; top:0; left:0; width:100%; height:100%; 
            background: rgba(255,255,255,0.8); display: flex; justify-content: center; align-items: center; z-index: 10;
            font-size: 1.5em; color: #666;
        }}
    </style>
</head>
<body>

    <div id="plot-container">
        <div id="loading">Loading Data...</div>
        <div id="plotly-div" style="width:100%; height:100%;"></div>
    </div>

    <script>
        // --- 1. Data Injection ---
        // Pre-computed initial state form Python
        const initialData = {initial_data_json};
        const initialLayout = {layout_json};
        
        // Data needed for dynamic updates
        const regions = {json.dumps(regions_order)};
        const dates = {json.dumps(dates)};
        const levelsData = {json.dumps(levels_data)}; // Date -> [Level array 1-15]
        const rawData = {json.dumps(raw_data)};       // Date -> [Raw Count array]
        
        const baseGrid = new Int8Array({base_grid_flat_json}); 
        
        const width = {WIDTH};
        const height = {HEIGHT};
        const CAP_NUM = {CAP_NUM};
        
        // --- 2. Initial Render & Helper Functions ---
        
        // Render initial plot immediately
        Plotly.newPlot('plotly-div', initialData, initialLayout).then(() => {{
            document.getElementById('loading').style.display = 'none';
        }});
        
        // JS Helper to build surface for updates
        function build3DSurface(date) {{
            const levels = levelsData[date];
            if (!levels) return null;
            
            const z = [];
            let idx = 0;
            for (let r = 0; r < height; r++) {{
                const row = new Float32Array(width);
                for (let c = 0; c < width; c++) {{
                    const val = baseGrid[idx];
                    idx++;
                    if (val === -1) {{
                        row[c] = NaN;
                    }} else if (val === -2) {{
                        row[c] = 0;
                    }} else {{
                        row[c] = levels[val];
                    }}
                }}
                z.push(row);
            }}
            return z;
        }}
        
        function get2DViewDetails(date) {{
             const vals = rawData[date];
             let dailyMax = 0;
             for(let v of vals) if(v > dailyMax) dailyMax = v;
             const viewMax = (dailyMax > CAP_NUM) ? CAP_NUM : (dailyMax > 0 ? dailyMax : 1);
             const text = regions.map((r, i) => `${{r}}: ${{vals[i]}}`);
             return {{ z: vals, zmax: viewMax, text: text }};
        }}
        
        // --- 3. Event Handling ---
        const plotDiv = document.getElementById('plotly-div');
        
        plotDiv.on('plotly_sliderchange', function(e) {{
            const date = e.step.label;
            
            // Generate Data
            const newZ3d = build3DSurface(date);
            const d2 = get2DViewDetails(date);
            
            // Update Data Only (Restyle) - Does not change visibility
            Plotly.restyle('plotly-div', {{
                z: [newZ3d, d2.z],
                text: [null, d2.text], // Only map needs text
                zmax: [null, d2.zmax]  // Only map needs zmax update
            }}, [0, 1]);
            
            // Update Title
            Plotly.relayout('plotly-div', {{title: `COVID-19 Confirmed Cases - ${{date}}`}});
        }});
        
        window.addEventListener('resize', () => {{
            Plotly.Plots.resize(plotDiv);
        }});

    </script>
</body>
</html>
    """
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Saved to {output_path}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="Start_Covid_Dashboard.html")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    
    geojson_path = script_dir / 'korea_provinces.json'
    csv_path = repo_root / 'data' / 'kr_regional_daily_excel.csv'
    
    if not csv_path.exists():
        csv_path = script_dir.parent / 'data' / 'kr_regional_daily_excel.csv'
        
    print(f"CSV Path: {csv_path}")
    
    df, geojson, geojson_str = load_data(csv_path, geojson_path)
    regions_order, dates, levels_data, raw_data = process_names_and_dates(df, geojson)
    base_grid = generate_base_grid(geojson, regions_order)
    # Pass geojson object too for python trace construction
    generate_html(script_dir / args.output, regions_order, dates, levels_data, raw_data, base_grid, geojson, geojson_str)

if __name__ == "__main__":
    main()
