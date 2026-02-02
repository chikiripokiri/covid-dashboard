import json
import requests
import random
import os

# 1. Load South Korea GeoJSON (Provinces)
# Using the southkorea-maps repository (skorea-provinces-geo.json)
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
# This simulates data like population density or other metrics
for feature in sk_geojson['features']:
    # Random height value between 2000 and 10000
    feature['properties']['Value'] = random.randint(2000, 10000)

# 2. Construct the Plotly JSON payload manually
# We create the figure structure as a dictionary.
# This bypasses the 'plotly.graph_objects' validation which might reject 'fill-extrusion'.
payload_data = [] # No standard traces, we use layout.mapbox.layers

payload_layout = {
    "title": "3D Extruded Map of South Korea",
    "autosize": True,
    "mapbox": {
        "style": "carto-positron", # A nice light basemap that doesn't usually require a token
        "center": {"lon": 127.5, "lat": 36.0},
        "zoom": 6,
        "pitch": 50, # Tilt the map to see 3D effect
        "bearing": 0,
        "layers": [
            {
                "sourcetype": "geojson",
                "source": sk_geojson,
                "type": "fill-extrusion", # This is the key property for 3D extrusion
                "paint": {
                    # Map 'Value' property to color (Linear interpolation)
                    "fill-extrusion-color": [
                        "interpolate", ["linear"], ["get", "Value"],
                        0, "#3c4e5a",      # Low value color
                        5000, "#e67e22",   # Mid value color
                        10000, "#e74c3c"   # High value color
                    ],
                    # Map 'Value' property to height
                    "fill-extrusion-height": ["get", "Value"],
                    "fill-extrusion-base": 0,
                    "fill-extrusion-opacity": 0.9
                }
            }
        ]
    },
    "margin": {"r":0,"t":40,"l":0,"b":0}
}

# 3. Generate the HTML file
# We inject the JSON data directly into a simple HTML template that loads Plotly.js
html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>3D Extruded Map of South Korea</title>
    <!-- Load latest Plotly.js -->
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        body, html {{ margin: 0; padding: 0; height: 100%; }}
        #myDiv {{ width: 100%; height: 100vh; }}
    </style>
</head>
<body>
    <div id="myDiv"></div>
    <script>
        var data = {json.dumps(payload_data)};
        var layout = {json.dumps(payload_layout)};
        var config = {{responsive: true, displayModeBar: true}};
        
        Plotly.newPlot('myDiv', data, layout, config);
    </script>
</body>
</html>
"""

output_file = "korea_3d_map.html"
try:
    with open(output_file, "w") as f:
        f.write(html_content)
    print(f"Success! Map saved to {output_file}")
    print("Please open this file in your browser to interact with the 3D map.")
except Exception as e:
    print(f"Error saving HTML: {e}")
