from pathlib import Path
import argparse
import json
import sys

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import plotly.io as pio


def load_data(csv_path: Path) -> pd.DataFrame:
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")
    df = pd.read_csv(csv_path)
    required = {"date", "region", "death"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in CSV: {', '.join(sorted(missing))}")
    return df


def build_html(df: pd.DataFrame, initial_date: str, output_file: Path) -> Path:
    # Normalize dates
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"].astype(str), format="%Y%m%d")

    # Colors per region (stable)
    regions = sorted(df["region"].unique())
    palette = px.colors.qualitative.Set3 + px.colors.qualitative.Plotly
    if len(palette) < len(regions):
        palette *= (len(regions) // len(palette) + 1)
    color_map = dict(zip(regions, palette))

    # Map date -> data (avoid include_groups warning by iterating manually)
    data_map = {}
    for date, g in df.groupby("date", sort=True):
        g_sorted = g.sort_values("death", ascending=False)
        iso = pd.to_datetime(date).date().isoformat()
        data_map[iso] = {
            "labels": g_sorted["region"].tolist(),
            "values": g_sorted["death"].tolist(),
            "colors": [color_map[r] for r in g_sorted["region"]],
        }

    dates_sorted = sorted(data_map.keys())
    earliest = dates_sorted[0]
    latest = dates_sorted[-1]

    # Initial date: prefer first date with deaths>0 to avoid empty pie; fallback to requested
    initial_iso = pd.to_datetime(initial_date, format="%Y%m%d").date().isoformat()
    if initial_iso not in data_map:
        raise ValueError(f"No data for date {initial_iso}.")
    nonzero_dates = [d for d in dates_sorted if sum(data_map[d]["values"]) > 0]
    start_iso = nonzero_dates[0] if nonzero_dates else initial_iso

    init = data_map[start_iso]
    fig = go.Figure(
        data=[
            go.Pie(
                labels=init["labels"],
                values=init["values"],
                marker=dict(colors=init["colors"]),
                hole=0.2,
                textinfo="label+percent",
                pull=0.03,
                hovertemplate="%{label}<br>Deaths: %{value}<extra></extra>",
                scalegroup="all",  # keep radius consistent across updates
            )
        ]
    )
    fig.update_layout(
        title="COVID-19 Deaths by Region",
        legend_title_text="Region",
        margin=dict(l=20, r=20, t=40, b=20),
        height=600,
        width=600,
        uniformtext_mode="hide",
    )

    # Plotly div+script (no full HTML)
    plot_html = pio.to_html(
        fig,
        include_plotlyjs="inline",
        full_html=False,
        default_width="100%",
        default_height="100%",
    )

    # Compose custom HTML with date picker
    custom_html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <title>COVID-19 사망자 파이차트 (날짜 선택)</title>
  <style>
    body {{ font-family: Arial, sans-serif; display:flex; flex-direction:column; align-items:center; gap:12px; margin:16px; }}
    .controls {{ display:flex; align-items:center; gap:8px; flex-wrap:wrap; }}
    #chart-container {{ width: 640px; height: 640px; }}
  </style>
</head>
<body>
  <div class="controls">
    <label for="datePicker">날짜 선택:</label>
    <input type="date" id="datePicker" min="{earliest}" max="{latest}" value="{start_iso}">
    <span id="currentDate">{start_iso}</span>
    <span id="status" style="color:#d33;font-weight:600;display:none;">해당 날짜는 사망자가 0명입니다.</span>
  </div>
  <div id="chart-container">
    {plot_html}
  </div>
  <script>
    const dataMap = {json.dumps(data_map)};
    const dateInput = document.getElementById('datePicker');
    const dateLabel = document.getElementById('currentDate');
    const status = document.getElementById('status');
    const plotDiv = document.querySelector('#chart-container').firstElementChild;

    function updateChart(isoDate) {{
      const entry = dataMap[isoDate];
      if (!entry) return;
      const total = entry.values.reduce((a,b)=>a+b,0);
      status.style.display = total === 0 ? 'inline' : 'none';

      // Filter out zero slices to avoid collapsed labels
      const filtered = entry.values.map((v,i)=>({{v,i}})).filter(it => it.v > 0);
      const labels = filtered.length ? filtered.map(it => entry.labels[it.i]) : ['No deaths'];
      const values = filtered.length ? filtered.map(it => entry.values[it.i]) : [1];
      const colors = filtered.length ? filtered.map(it => entry.colors[it.i]) : ['#cccccc'];

      // Hide labels only for very small slices (<5% of total) to avoid overlap
      const tot = values.reduce((a,b)=>a+b,0) || 1;
      const text = values.map((v,i)=> (v/tot) >= 0.05 ? `${{labels[i]}}<br>${{(v/tot*100).toFixed(1)}}%` : '');

      Plotly.react(plotDiv, [{{ 
        type: 'pie',
        labels: labels,
        values: values,
        marker: {{color: colors}},
        hole: 0.2,
        text: text,
        textinfo: 'text',
        textposition: 'inside',
        hovertemplate: '%{{label}}<br>Deaths: %{{value}}<extra></extra>',
        pull: 0.02,
        scalegroup: 'all',
        insidetextorientation: 'radial'
      }}], {{ 
        title: 'COVID-19 Deaths by Region',
        legend: {{title: {{text: 'Region'}}}},
        margin: {{l:20,r:20,t:40,b:20}},
        height: 600,
        width: 600,
        uniformtext: {{mode: 'hide'}}
      }}, {{responsive: true}});
      dateLabel.textContent = isoDate;
    }}

    dateInput.addEventListener('change', (e) => {{
      updateChart(e.target.value);
    }});

    dateInput.value = "{start_iso}";
    updateChart("{start_iso}");
  </script>
</body>
</html>
"""

    output_file.write_text(custom_html, encoding="utf-8")
    return output_file


def main():
    parser = argparse.ArgumentParser(description="Plot deaths by region as a pie chart with calendar picker.")
    parser.add_argument(
        "--date",
        type=int,
        default=None,
        help="Initial date in YYYYMMDD (default: first date in CSV).",
    )
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    data_csv = repo_root / "data" / "kr_regional_daily_excel.csv"
    output_file = script_dir / "korea_covid_death_pie.html"

    df = load_data(data_csv)
    initial_date = str(args.date or int(df["date"].min()))

    try:
        saved = build_html(df, initial_date, output_file)
    except (FileNotFoundError, ValueError) as e:
        print(e, file=sys.stderr)
        sys.exit(1)

    print(f"Saved pie chart to {saved}")


if __name__ == "__main__":
    main()
