import json
import requests
import random
import plotly.io as pio
import plotly.graph_objects as go
import plotly

# 1. Load South Korea GeoJSON (Provinces)
geojson_url = 'https://raw.githubusercontent.com/southkorea/southkorea-maps/master/gadm/json/skorea-provinces-geo.json'

print("Downloading GeoJSON...")
try:
    response = requests.get(geojson_url)
    response.raise_for_status()
    sk_geojson = response.json()
except Exception as e:
    print(f"Error downloading GeoJSON: {e}")
    exit()

print("Processing Data...")

# Add a 'Value' property to each feature for extrusion
for feature in sk_geojson['features']:
    # Random height value between 1000 and 10000
    feature['properties']['Value'] = random.randint(1000, 10000)

# 2. Define the Plotly Figure as a standard Python Dictionary
# This bypasses strict validation in older plotly python versions
fig_dict = {
    "data": [], # No data traces needed, we use layout.mapbox.layers
    "layout": {
        "title": "3D Extruded Map of South Korea",
        "mapbox": {
            "style": "carto-positron",
            "center": {"lon": 127.5, "lat": 36.0},
            "zoom": 6,
            "pitch": 45,
            "bearing": 0,
            "layers": [
                {
                    "sourcetype": "geojson",
                    "source": sk_geojson,
                    "type": "fill-extrusion",
                    "minzoom": 0,
                    "paint": {
                        "fill-extrusion-color": [
                            "interpolate", ["linear"], ["get", "Value"],
                            1000, "blue",
                            5000, "yellow",
                            10000, "red"
                        ],
                        "fill-extrusion-height": ["get", "Value"],
                        "fill-extrusion-base": 0,
                        "fill-extrusion-opacity": 0.8
                    }
                }
            ]
        },
        "margin": {"r":0,"t":40,"l":0,"b":0}
    }
}

print("Generating HTML...")

# 3. Save to HTML
# Use skip_invalid=True to bypass the strict validation for 'fill-extrusion'
output_file = "korea_3d_map.html"
try:
    fig = go.Figure(fig_dict, skip_invalid=True)
    fig.write_html(output_file, validate=False)
    print(f"Success! Map saved to {output_file}")
    print("Please open this file in your browser to view the 3D map.")
except Exception as e:
    print(f"Error saving HTML: {e}")
