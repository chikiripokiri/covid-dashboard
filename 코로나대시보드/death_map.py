from pathlib import Path
import argparse
import json
import sys

import pandas as pd
import plotly.express as px


def build(html_out: Path, csv_path: Path, geojson_path: Path, initial_date: int | None):
    if not csv_path.exists():
        raise FileNotFoundError(csv_path)
    if not geojson_path.exists():
        raise FileNotFoundError(geojson_path)

    df = pd.read_csv(csv_path)
    if not {"date", "region", "death"}.issubset(df.columns):
        raise ValueError("CSV must contain columns: date, region, death")

    geojson = json.loads(geojson_path.read_text(encoding="utf-8"))
    geojson_js = geojson_path.read_text(encoding="utf-8")
    regions_order = [f["properties"]["CTP_ENG_NM"] for f in geojson["features"]]

    # Region name aliases (CSV may use shortened Korean names)
    # Map various CSV labels to GeoJSON canonical names
    region_alias = {
        # English short → canonical
        "Seoul": "Seoul",
        "Busan": "Busan",
        "Daegu": "Daegu",
        "Incheon": "Incheon",
        "Gwangju": "Gwangju",
        "Daejeon": "Daejeon",
        "Ulsan": "Ulsan",
        "Sejong": "Sejong-si",
        "Sejong-si": "Sejong-si",
        "Gyeonggi": "Gyeonggi-do",
        "Gangwon": "Gangwon-do",
        "Chungbuk": "Chungcheongbuk-do",
        "Chungnam": "Chungcheongnam-do",
        "Jeonbuk": "Jeollabuk-do",
        "Jeonnam": "Jellanam-do",  # note spelling in GeoJSON
        "Gyeongbuk": "Gyeongsangbuk-do",
        "Gyeongnam": "Gyeongsangnam-do",
        "Jeju": "Jeju-do",
        "Quarantine": "Quarantine",  # will be ignored if not in geojson
        # Korean short → canonical
        "서울": "Seoul",
        "부산": "Busan",
        "대구": "Daegu",
        "인천": "Incheon",
        "광주": "Gwangju",
        "대전": "Daejeon",
        "울산": "Ulsan",
        "세종": "Sejong-si",
        "경기": "Gyeonggi-do",
        "경기도": "Gyeonggi-do",
        "강원": "Gangwon-do",
        "강원도": "Gangwon-do",
        "충북": "Chungcheongbuk-do",
        "충청북도": "Chungcheongbuk-do",
        "충남": "Chungcheongnam-do",
        "충청남도": "Chungcheongnam-do",
        "전북": "Jeollabuk-do",
        "전라북도": "Jeollabuk-do",
        "전남": "Jellanam-do",
        "전라남도": "Jellanam-do",
        "경북": "Gyeongsangbuk-do",
        "경상북도": "Gyeongsangbuk-do",
        "경남": "Gyeongsangnam-do",
        "경상남도": "Gyeongsangnam-do",
        "제주": "Jeju-do",
        "제주도": "Jeju-do",
    }

    # Precompute deaths per region per date aligned to regions_order
    date_groups = {}
    for date, g in df.groupby("date", sort=True):
        deaths = {r: 0 for r in regions_order}
        for _, row in g.iterrows():
            reg = str(row["region"])
            reg = region_alias.get(reg, reg)
            if reg not in deaths and f"{reg}-do" in deaths:
                reg = f"{reg}-do"
            if reg not in deaths and f"{reg}-si" in deaths:
                reg = f"{reg}-si"
            if reg in deaths:
                deaths[reg] += int(row["death"])
        date_groups[str(int(date))] = [deaths[r] for r in regions_order]

    dates_sorted = sorted(date_groups.keys())
    if not dates_sorted:
        raise ValueError("No data found.")

    # Choose initial date: first nonzero deaths if available, else latest
    first_nonzero = next((d for d in dates_sorted if sum(date_groups[d]) > 0), dates_sorted[-1])
    init_date = str(initial_date) if initial_date else first_nonzero
    if init_date not in date_groups:
        init_date = first_nonzero

    init_vals = date_groups[init_date]
    init_max = max(init_vals) or 1
    global_max = max(max(vals) for vals in date_groups.values()) or 1

    fig = px.choropleth(
        locations=regions_order,
        geojson=geojson,
        featureidkey="properties.CTP_ENG_NM",
        color=init_vals,
        color_continuous_scale="Reds",
        range_color=(0, init_max),
        title=f"COVID-19 Deaths by Region - {init_date}",
    )
    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(
        margin=dict(l=0, r=0, t=50, b=0),
        height=950,
        width=950,
        coloraxis_colorbar=dict(lenmode="pixels", len=600, thickness=26, yanchor="middle", y=0.5),
    )

    # Embed custom JS for date picker
    plot_html = fig.to_html(include_plotlyjs="inline", full_html=False)
    data_js = json.dumps(date_groups)
    regions_js = json.dumps(regions_order)

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <title>COVID-19 사망자 지도</title>
  <style>
    body {{ font-family: Arial, sans-serif; display:flex; flex-direction:column; align-items:center; gap:12px; margin:16px; }}
    .controls {{ display:flex; align-items:center; gap:8px; flex-wrap:wrap; }}
    #chart {{ width: 720px; }}
    #status {{ color:#d33; font-weight:600; display:none; }}
  </style>
</head>
<body>
  <div class="controls">
    <label for="datePicker">날짜 선택:</label>
    <input type="date" id="datePicker" min="{dates_sorted[0][:4]}-{dates_sorted[0][4:6]}-{dates_sorted[0][6:]}" max="{dates_sorted[-1][:4]}-{dates_sorted[-1][4:6]}-{dates_sorted[-1][6:]}" value="{init_date[:4]}-{init_date[4:6]}-{init_date[6:]}">
    <span id="currentDate">{init_date}</span>
    <span id="status">해당 날짜는 사망자가 0명입니다.</span>
  </div>
  <div id="chart" style="width: 980px; max-width: 100%;">
    {plot_html}
  </div>
  <script>
    const dataMap = {data_js};
    const regions = {regions_js};
    const geojson = {geojson_js};
    const dateInput = document.getElementById('datePicker');
    const dateLabel = document.getElementById('currentDate');
    const status = document.getElementById('status');
    const plotDiv = document.querySelector('#chart').firstElementChild;
    const maxValAll = {global_max};

    function fmtDate(dateStr) {{
      return dateStr.replace(/-/g, '');
    }}

    const baseLayout = {{
      geo: {{fitbounds:'locations', visible:false}},
      margin: {{l:0, r:0, t:50, b:0}},
      height: 950,
      width: 950,
      coloraxis: {{
        cmin: 0,
        cmax: {global_max},
        colorscale: 'Reds',
        colorbar: {{lenmode:'pixels', len:600, thickness:26, yanchor:'middle', y:0.5}}
      }}
    }};

    function update(dateStrDash) {{
      const key = fmtDate(dateStrDash);
      const vals = dataMap[key];
      if (!vals) {{
        status.textContent = '해당 날짜 데이터가 없습니다.';
        status.style.display = 'inline';
        return;
      }}
      const total = vals.reduce((a,b)=>a+b,0);
      status.style.display = total === 0 ? 'inline' : 'none';

      const localMax = Math.max(...vals, 1);

      const data = [{{
        type: 'choropleth',
        locations: regions,
        z: vals,
        geojson: geojson,
        featureidkey: 'properties.CTP_ENG_NM',
        colorscale: 'Reds',
        zmin: 0,
        zmax: localMax,
        text: vals.map((v,i)=>`${{regions[i]}}: ${{v.toLocaleString()}}`),
        coloraxis: 'coloraxis',
        hovertemplate: '%{{text}}<extra></extra>'
      }}];

      const layout = {{
        ...baseLayout,
        coloraxis: {{...baseLayout.coloraxis, cmax: localMax}},
        title: `COVID-19 Deaths by Region - ${{key}}`
      }};

      Plotly.react(plotDiv, data, layout, {{responsive: true}});
      dateLabel.textContent = key;
    }}

    dateInput.addEventListener('change', (e)=>update(e.target.value));
    update(dateInput.value);
  </script>
</body>
</html>
"""

    html_out.write_text(html, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Make Korea COVID-19 death choropleth map with date picker.")
    parser.add_argument("--date", type=int, default=None, help="Initial date YYYYMMDD (defaults to latest).")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    csv_path = repo_root / "data" / "kr_regional_daily_excel.csv"
    geojson_path = script_dir / "korea_provinces.json"
    output_path = script_dir / "korea_covid_death_map.html"

    try:
        build(output_path, csv_path, geojson_path, args.date)
    except Exception as e:
        print(e, file=sys.stderr)
        sys.exit(1)

    print(f"Saved map to {output_path}")


if __name__ == "__main__":
    main()
