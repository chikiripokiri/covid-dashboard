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
# 2. Helpers from 3D Map Code
# ---------------------------------------------------------
def get_height_level(confirmed_cases):
    """
    Scale confirmed cases to height level (1-18).
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
        # The file might have different columns or need cleaning.
        # Based on previous files, 'death' is in death_map.py, 'confirmed' in 3d map.
        # Let's check if they exist. If 'death' is missing (maybe separate files?), logic handles it.
        # Assuming the CSV provided has both as per user context implies they effectively use the same source or similar.
        pass

    df['date'] = df['date'].astype(str)
    
    return df, geojson, geojson_str

def process_names_and_dates(df, geojson):
    # Extract canonical names from GeoJSON (ordering matters for the mask)
    # We use CTP_ENG_NM as the key ID
    regions_order = [f["properties"]["CTP_ENG_NM"] for f in geojson["features"]]
    region_kor_map = {f["properties"]["CTP_ENG_NM"]: f["properties"]["CTP_KOR_NM"] for f in geojson["features"]}

    # Region Alias Map (from death_map.py) to unify CSV names to GeoJSON
    region_alias = {
        "Seoul": "Seoul", "Busan": "Busan", "Daegu": "Daegu", "Incheon": "Incheon",
        "Gwangju": "Gwangju", "Daejeon": "Daejeon", "Ulsan": "Ulsan", "Sejong": "Sejong-si",
        "Sejong-si": "Sejong-si", "Gyeonggi": "Gyeonggi-do", "Gangwon": "Gangwon-do",
        "Chungbuk": "Chungcheongbuk-do", "Chungnam": "Chungcheongnam-do",
        "Jeonbuk": "Jeollabuk-do", "Jeonnam": "Jellanam-do",
        "Gyeongbuk": "Gyeongsangbuk-do", "Gyeongnam": "Gyeongsangnam-do",
        "Jeju": "Jeju-do",
        # Korean inputs
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
    # We want two dicts: date -> [confirmed_levels], date -> [deaths]
    # The arrays must be aligned with regions_order
    
    date_groups_confirmed = {}
    date_groups_deaths = {}
    
    dates_sorted = sorted(df['date'].unique())
    
    print("Processing daily data...")
    
    for date in dates_sorted:
        day_df = df[df['date'] == date]
        
        # Initialize counts
        conf_map = {r: 0 for r in regions_order}
        death_map = {r: 0 for r in regions_order}
        
        for _, row in day_df.iterrows():
            reg_raw = str(row['region'])
            reg = region_alias.get(reg_raw, reg_raw)
            # Try appending -do or -si if not found (simple heuristics from death_map.py)
            if reg not in conf_map:
                if f"{reg}-do" in conf_map: reg = f"{reg}-do"
                elif f"{reg}-si" in conf_map: reg = f"{reg}-si"
            
            if reg in conf_map:
                conf_map[reg] += int(row.get('confirmed', 0))
                death_map[reg] += int(row.get('death', 0))
        
        # Convert Confirmed to Level
        levels = [get_height_level(conf_map[r]) for r in regions_order]
        deaths = [death_map[r] for r in regions_order]
        
        date_groups_confirmed[date] = levels
        date_groups_deaths[date] = deaths

    return regions_order, dates_sorted, date_groups_confirmed, date_groups_deaths

def generate_base_grid(geojson, regions_order):
    """
    Generates a grid (flattened for JS) where pixel values represent:
    -1: Sea/Ignore
    -2: Skirt (Elevation 0)
    0..N: Region Index
    """
    print("Generating 3D Base Grid...")
    
    # 1. Create a mask for each region
    # We will use an integer grid.
    # Initialize with -1 (Sea)
    grid = np.full(GRID_SHAPE, -1, dtype=np.int32)
    
    for idx, region_name in enumerate(regions_order):
        # Find feature
        feature = next(f for f in geojson['features'] if f['properties']['CTP_ENG_NM'] == region_name)
        geom = get_largest_polygon(feature['geometry'])
        
        # Rasterize this single region
        # We burn the value 'idx' into the grid where the polygon matches
        # Note: 'all_touched' can be True or False. True makes it thicker.
        mask = features.rasterize(
            [(geom, 1)],
            out_shape=GRID_SHAPE,
            transform=AFF_TRANS,
            fill=0,
            dtype='uint8'
        )
        # Update main grid
        grid[mask == 1] = idx

    # 2. Generate Skirt
    # Identify valid pixels (>=0)
    valid_mask = grid >= 0
    # Dilate to find shoreline
    shoreline_mask = binary_dilation(valid_mask, iterations=1) & ~valid_mask
    # Set skirt pixels to -2
    grid[shoreline_mask] = -2
    
    return grid

# ---------------------------------------------------------
# 4. HTML Generation
# ---------------------------------------------------------
def generate_html(output_path, regions_order, dates, confirmed_data, death_data, base_grid, geojson_str):
    print("Generating HTML...")
    
    # Flatten base grid for efficient JSON embedding
    # It's 500*600 = 300,000 items. 
    base_grid_flat = base_grid.flatten().tolist()
    
    # Find global max for 2D map to set static color range or dynamic?
    # death_map.py calculates global max.
    all_deaths = []
    for d_list in death_data.values():
        all_deaths.extend(d_list)
    max_death = max(all_deaths) if all_deaths else 1
    
    # Initial Date
    init_date = dates[-1]
    
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
            margin: 0; padding: 10px; 
            background: #f4f4f9; 
            height: 100vh; 
            display: flex; 
            flex-direction: column; 
            align-items: center; 
            overflow: hidden; /* Prevent scrolling */
        }}
        header {{ margin-bottom: 10px; text-align: center; flex-shrink: 0; }}
        h1 {{ margin: 0; font-size: 1.5rem; color: #333; }}
        
        .controls {{ 
            background: white; padding: 10px 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); 
            display: flex; gap: 20px; align-items: center; margin-bottom: 10px; flex-wrap: wrap; justify-content: center;
            flex-shrink: 0;
            z-index: 20;
        }}
        .control-group {{ display: flex; flex-direction: column; gap: 3px; align-items: center; }}
        .control-group label {{ font-weight: bold; font-size: 0.8rem; color: #555; }}
        select, input[type="range"], input[type="date"] {{ padding: 2px; border: 1px solid #ddd; border-radius: 4px; }}
        
        .btn-group {{ display: flex; gap: 0; border: 1px solid #ccc; border-radius: 5px; overflow: hidden; }}
        .btn-group button {{ 
            border: none; padding: 5px 15px; cursor: pointer; background: #f9f9f9; font-size: 0.9rem; font-weight: bold; 
            transition: background 0.2s;
        }}
        .btn-group button.active {{ background: #007bff; color: white; }}
        .btn-group button:not(:last-child) {{ border-right: 1px solid #ccc; }}
        
        #plot-container {{ 
            flex: 1; /* Take remaining height */
            width: 100%; 
            max-width: 1200px;
            min-height: 0; /* Important for flex child scaling */
            background: white; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); 
            position: relative;
            display: flex;
            justify-content: center;
            align-items: center;
        }}
        #loading {{ 
            position: absolute; top:0; left:0; width:100%; height:100%; 
            background: rgba(255,255,255,0.8); display: flex; justify-content: center; align-items: center; z-index: 10;
            font-size: 1.5em; color: #666;
        }}
    </style>
</head>
<body>

    <header>
        <h1>KOREA COVID-19 DASHBOARD</h1>
    </header>
    
    <div class="controls">
        <div class="control-group">
            <label>Visualization Mode</label>
            <div class="btn-group">
                <button id="btn-3d" class="active" onclick="setMode('3d')">3D Confirmed</button>
                <button id="btn-2d" onclick="setMode('2d')">2D Deaths</button>
            </div>
        </div>
        
        <div class="control-group" style="width: 300px;">
            <label>Date Selection: <span id="date-display">{init_date}</span></label>
            <input type="range" id="date-slider" min="0" max="{len(dates)-1}" value="{len(dates)-1}" style="width: 100%;">
        </div>
    </div>

    <div id="plot-container">
        <div id="loading">Loading Data...</div>
        <div id="plotly-div" style="width:100%; height:100%;"></div>
    </div>

    <script>
        // --- 1. Data Injection ---
        const regions = {json.dumps(regions_order)};
        const dates = {json.dumps(dates)};
        const confirmedData = {json.dumps(confirmed_data)}; // Date -> [Level array]
        const deathData = {json.dumps(death_data)};         // Date -> [Death array]
        
        // Base Grid for 3D: Flattened array 
        // -1: Sea, -2: Skirt, 0+ Region Index
        const baseGrid = new Int8Array({json.dumps(base_grid_flat)}); 
        const geojson = {geojson_str};
        
        const width = {WIDTH};
        const height = {HEIGHT};
        const maxDeath = {max_death};
        
        // --- 2. State ---
        let currentMode = '3d'; // '3d' or '2d'
        let currentIndex = dates.length - 1;
        
        const plotDiv = document.getElementById('plotly-div');
        const slider = document.getElementById('date-slider');
        const dateDisplay = document.getElementById('date-display');
        const btn3d = document.getElementById('btn-3d');
        const btn2d = document.getElementById('btn-2d');
        const loading = document.getElementById('loading');

        // --- 3. 3D Helper Functions ---
        const xCoords = Array.from({{length: width}}, (_, i) => {MIN_LON} + i * {RES_LON});
        const yCoords = Array.from({{length: height}}, (_, i) => {MAX_LAT} - i * {RES_LAT});
        
        function build3DSurface(date) {{
            const levels = confirmedData[date];
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

        const layout3D = {{
            title: 'COVID-19 3D Confirmed Cases (Level 1-18)',
            scene: {{
                xaxis: {{visible: false}},
                yaxis: {{visible: false}},
                zaxis: {{title: 'Level', visible: false}},
                aspectmode: 'manual',
                aspectratio: {{x: 1, y: 1.85, z: 0.5}},
                camera: {{eye: {{x: 1.5, y: -1.5, z: 0.8}}}}
            }},
            margin: {{l:0, r:0, b:20, t:50}},
            autosize: true
        }};
        
        const layout2D = {{
            title: 'COVID-19 Deaths (2D)',
            geo: {{fitbounds: 'locations', visible: false}},
            margin: {{l:0, r:0, b:20, t:50}},
            coloraxis: {{
                cmin: 0, cmax: maxDeath, colorscale: 'Reds',
                colorbar: {{len: 0.8, title: 'Deaths'}}
            }},
            autosize: true
        }};

        // --- 4. Main Rendering Logic ---
        function render() {{
            const date = dates[currentIndex];
            dateDisplay.textContent = date;
            
            if (currentMode === '3d') {{
                const zData = build3DSurface(date);
                
                const data3d = [{{
                    type: 'surface',
                    z: zData,
                    x: xCoords,
                    y: yCoords,
                    colorscale: [
                        [0, "#6bb5ff"],
                        [0.277, "#b590b5"],
                        [1.0, "#ff6b6b"]
                    ],
                    cmin: 0, cmax: 18,
                    showscale: false,
                    contours: {{z: {{show: true, usecolormap: true, highlightcolor: "white", project: {{z: true}}}} }},
                    lighting: {{ambient: 0.6, roughness: 0.1, diffuse: 0.8, fresnel: 0.2, specular: 0.5}}
                }}];
                
                const currentData = document.getElementById('plotly-div').data;
                const isSameType = currentData && currentData[0] && currentData[0].type === 'surface';
                
                if (isSameType) {{
                    Plotly.react('plotly-div', data3d, layout3D);
                }} else {{
                    Plotly.newPlot('plotly-div', data3d, layout3D, {{responsive: true}}).then(() => loading.style.display = 'none');
                }}
                
            }} else {{
                // 2D Mode
                const vals = deathData[date];
                const data2d = [{{
                    type: 'choropleth',
                    locations: regions,
                    z: vals,
                    geojson: geojson,
                    featureidkey: 'properties.CTP_ENG_NM',
                    colorscale: 'Reds',
                    zmin: 0, zmax: maxDeath,
                    text: regions.map((r, i) => `${{r}}: ${{vals[i]}}`),
                    hovertemplate: '%{{text}}<extra></extra>'
                }}];
                
                const currentData = document.getElementById('plotly-div').data;
                const isSameType = currentData && currentData[0] && currentData[0].type === 'choropleth';
                
                const thisLayout = {{...layout2D, title: `COVID-19 Deaths - ${{date}}`}};
                
                if (isSameType) {{
                     Plotly.react('plotly-div', data2d, thisLayout);
                }} else {{
                     Plotly.newPlot('plotly-div', data2d, thisLayout, {{responsive: true}}).then(() => loading.style.display = 'none');
                }}
            }}
        }}

        // --- 5. Event Listeners ---
        window.setMode = (mode) => {{
            currentMode = mode;
            if (mode === '3d') {{
                btn3d.classList.add('active');
                btn2d.classList.remove('active');
            }} else {{
                btn2d.classList.add('active');
                btn3d.classList.remove('active');
            }}
            loading.style.display = 'flex';
            setTimeout(render, 50);
        }};
        
        slider.addEventListener('input', (e) => {{
            currentIndex = parseInt(e.target.value);
            render();
        }});
        
        // Handle Resize
        window.addEventListener('resize', () => {{
            Plotly.Plots.resize(plotDiv);
        }});

        setTimeout(render, 100);

    </script>
</body>
</html>
    """
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Saved to {output_path}")

# ---------------------------------------------------------
# Main
# ---------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Create Integrated 3D/2D Dashboard")
    parser.add_argument("--output", default="Start_Covid_Dashboard.html", help="Output HTML filename")
    args = parser.parse_args()

    # Paths (Assumed relative to script or specific structure)
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent # Assuming script is in a subdir like '코로나대시보드'
    
    # Adjust as per user's file locations in prompt
    # User file: /Users/parkhyunsik/파이썬/코로나대시보드_팀용/코로나대시보드/death_map.py
    # Data likely at ../data/kr_regional_daily_excel.csv
    
    geojson_path = script_dir / 'korea_provinces.json'
    csv_path = repo_root / 'data' / 'kr_regional_daily_excel.csv'
    
    if not csv_path.exists():
        # Fallback check
        csv_path = script_dir.parent / 'data' / 'kr_regional_daily_excel.csv'
        
    print(f"CSV Path: {csv_path}")
    print(f"GeoJSON Path: {geojson_path}")
    
    # 1. Load Data
    df, geojson, geojson_str = load_data(csv_path, geojson_path)
    
    # 2. Process Data
    regions_order, dates, conf_data, death_data = process_names_and_dates(df, geojson)
    
    # 3. Generate Base Grid
    base_grid = generate_base_grid(geojson, regions_order)
    
    # 4. Generate HTML
    generate_html(script_dir / args.output, regions_order, dates, conf_data, death_data, base_grid, geojson_str)

if __name__ == "__main__":
    main()
