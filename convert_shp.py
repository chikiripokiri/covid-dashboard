import geopandas as gpd
import json
import os

# Input and Output paths
shp_path = '/Users/parkhyunsik/Downloads/ctprvn_20230729/ctprvn.shp'
output_json = 'korea_provinces.json'

print(f"Loading SHP file: {shp_path}")

try:
    # 1. Load SHP file
    # Korean public data often uses 'euc-kr' or 'cp949' encoding
    gdf = gpd.read_file(shp_path, encoding='euc-kr')
    print("SHP loaded successfully.")
    print("Initial CRS:", gdf.crs)
    print("Columns:", gdf.columns)
    print(gdf.head())

    # 2. Check and Convert CRS
    # If CRS is missing or local, convert to WGS84 (EPSG:4326)
    if gdf.crs is None:
        print("Warning: CRS is missing. Assuming EPSG:5179 (common for Korean data).")
        gdf.set_crs(epsg=5179, inplace=True)
    
    if gdf.crs != 'epsg:4326':
        print("Converting CRS to EPSG:4326...")
        gdf = gdf.to_crs(epsg=4326)

    # 3. Simplify Geometry (Optional but recommended for web)
    print("Simplifying geometry...")
    gdf['geometry'] = gdf.simplify(tolerance=0.001, preserve_topology=True)

    # 4. Save to GeoJSON
    print(f"Saving to {output_json}...")
    gdf.to_file(output_json, driver='GeoJSON')
    print("Conversion complete!")

except Exception as e:
    print(f"Error during conversion: {e}")
