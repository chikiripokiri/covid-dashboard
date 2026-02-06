"""
Weekly regional confirmed-case share pie chart with week selector.

Usage:
    python 코로나대시보드/death_pie.py

Output:
    코로나대시보드/korea_covid_weekly_confirmed_pie.html
"""

from pathlib import Path
import argparse
import json
import sys

import pandas as pd
import plotly.express as px
import plotly.io as pio


def load_data(csv_path: Path) -> pd.DataFrame:
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")
    df = pd.read_csv(csv_path)
    required = {"date", "region", "confirmed"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in CSV: {', '.join(sorted(missing))}")
    return df


def build_html(df: pd.DataFrame, output_file: Path) -> Path:
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"].astype(str), format="%Y%m%d")

    # Week start (Monday) and labels
    df["week_start"] = df["date"] - pd.to_timedelta(df["date"].dt.weekday, unit="d")
    df["week_end"] = df["week_start"] + pd.Timedelta(days=6)
    df["week_key"] = df["week_start"].dt.strftime("%Y%m%d")
    df["week_display"] = (
        df["week_start"].dt.year.astype(str)
        + "년 "
        + df["week_start"].dt.month.astype(str)
        + "월 "
        + (((df["week_start"].dt.day - 1) // 7) + 1).astype(str)
        + "째주"
    )
    df["week_range"] = df["week_start"].dt.strftime("%Y-%m-%d") + "~" + df["week_end"].dt.strftime("%Y-%m-%d")

    regions = sorted(df["region"].unique())

    # 단일 고정 팔레트 (이외 지역은 회색)
    fixed_colors = {
        "Daegu": "#1f77b4",      # blue
        "Gyeonggi": "#d62728",   # red
        "Seoul": "#2ca02c",      # green
        "Busan": "#9467bd",
        "Incheon": "#8c564b",
        "Gwangju": "#e377c2",
        "Daejeon": "#7f7f7f",
        "Ulsan": "#bcbd22",
        "Sejong": "#17becf",
        "Gyeongbuk": "#aec7e8",
        "Gyeongnam": "#ff9896",
        "Chungbuk": "#98df8a",
        "Chungnam": "#c5b0d5",
        "Gangwon": "#c49c94",
        "Jeonbuk": "#f7b6d2",
        "Jeonnam": "#dbdb8d",
        "Jeju": "#9edae5",
        "Quarantine": "#c7c7c7",
    }
    color_map = {region: fixed_colors.get(region, "#999999") for region in regions}

    data_map = {}
    for wk, g in df.groupby("week_key"):
        g_sum = g.groupby("region")["confirmed"].sum()
        values = [int(g_sum.get(r, 0)) for r in regions]
        data_map[wk] = {
            "labels": regions,
            "values": values,
            "display_text": g["week_display"].iloc[0],
            "range_text": g["week_range"].iloc[0],
        }

    weeks_sorted = sorted(data_map.keys())
    if not weeks_sorted:
        raise ValueError("No data to plot.")
    nonzero_weeks = [w for w in weeks_sorted if sum(data_map[w]["values"]) > 0]
    start_week = nonzero_weeks[0] if nonzero_weeks else weeks_sorted[0]
    init = data_map[start_week]

    start_week_json = json.dumps(start_week)

    options_html = "\n".join(
        f'<option value="{wk}" {"selected" if wk==start_week else ""}>{data_map[wk]["display_text"]}</option>'
        for wk in weeks_sorted
    )

    custom_html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <title>주간 지역별 확진자 비율</title>
  <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
  <style>
    body {{ font-family: Arial, sans-serif; display:flex; flex-direction:column; align-items:center; gap:12px; margin:16px; }}
    .controls {{ display:flex; align-items:center; gap:8px; flex-wrap:wrap; }}
    #chart-container {{ width: 640px; height: 640px; }}
  </style>
</head>
<body>
  <div class="controls">
    <label for="weekSelect">주 선택:</label>
    <select id="weekSelect">
      {options_html}
    </select>
    <span id="rangeWeek">({data_map[start_week]["range_text"]})</span>
    <span id="status" style="color:#d33;font-weight:600;display:none;">해당 주는 확진자가 0명입니다.</span>
  </div>
  <div id="chart-container">
    <div id="chart"></div>
  </div>
  <script>
    const colorMap = {json.dumps(color_map)};
    const dataMap = {json.dumps(data_map)};
    const startWeek = {start_week_json};
    const weekSelect = document.getElementById('weekSelect');
    const rangeLabel = document.getElementById('rangeWeek');
    const status = document.getElementById('status');
    const plotDiv = document.getElementById('chart');

    function updateChart(weekKey) {{
      const entry = dataMap[weekKey];
      if (!entry) return;
      const total = entry.values.reduce((a,b)=>a+b,0);
      status.style.display = total === 0 ? 'inline' : 'none';

      const sorted = entry.values
        .map((v,i)=>({{v,i,label: entry.labels[i]}}))
        .sort((a,b)=>b.v - a.v);
      const nonZero = sorted.filter(it => it.v > 0);
      const labels = nonZero.length ? nonZero.map(it => it.label) : ['No cases'];
      const values = nonZero.length ? nonZero.map(it => it.v) : [1];
      const colors = nonZero.length ? nonZero.map(it => colorMap[it.label] || '#999999') : ['#cccccc'];

      const threshold = 0.12;
      const text = values.map((v,i)=> (i < 4 || (v/total) >= threshold) ? labels[i] : '');

      Plotly.react(plotDiv, [{{
        type: 'pie',
        labels: labels,
        values: values,
        marker: {{color: colors}},
        hole: 0.2,
        text: text,
        textinfo: 'text+percent',
        textposition: 'inside',
        textfont: {{size: 50}},
        pull: 0.03,
        scalegroup: 'all',
        hovertemplate: '%{{label}}<br>Confirmed: %{{value}}<extra></extra>',
        sort: false
      }}], {{
        title: `Weekly Confirmed Share by Region - ${{entry.display_text}} (${{entry.range_text}})`,
        legend: {{title: {{text: 'Region'}}}},
        margin: {{l:20,r:20,t:40,b:20}},
        height: 700,
        width: 700,
        uniformtext: {{mode: 'show', minsize: 14}}
      }}, {{responsive: true}});
      rangeLabel.textContent = `(${{entry.range_text}})`;
    }}

    weekSelect.addEventListener('change', (e) => {{
      updateChart(e.target.value);
    }});

    updateChart(startWeek);
  </script>
</body>
</html>
"""

    output_file.write_text(custom_html, encoding="utf-8")
    return output_file


def main():
    parser = argparse.ArgumentParser(description="Weekly regional confirmed-case share pie chart.")
    parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    data_csv = repo_root / "data" / "kr_regional_daily_excel.csv"
    output_file = script_dir / "korea_covid_weekly_confirmed_pie.html"

    df = load_data(data_csv)

    try:
        saved = build_html(df, output_file)
    except (FileNotFoundError, ValueError) as e:
        print(e, file=sys.stderr)
        sys.exit(1)

    print(f"Saved pie chart to {saved}")


if __name__ == "__main__":
    main()
