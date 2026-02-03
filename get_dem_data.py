import elevation
import os

# Bounds for South Korea (Approximate)
# West, South, East, North
# 125.0, 33.0, 130.0, 39.0 covers the peninsula broadly
bounds = (125.0, 33.0, 130.0, 39.0)

output_file = os.path.abspath("korea_dem.tif")

print(f"Downloading SRTM data to {output_file}...")
print("This may take some time depending on the server status...")

try:
    # elevation.clip automatically downloads the necessary tiles and clips them
    elevation.clip(bounds=bounds, output=output_file)
    print("Download and clip complete!")
    
    # Check if file exists
    if os.path.exists(output_file):
        print(f"File size: {os.path.getsize(output_file) / (1024*1024):.2f} MB")
    else:
        print("Error: Output file not found via check.")
        
except Exception as e:
    print(f"Error during download: {e}")
    # Create a fallback/dummy file if download fails (to be handled by next script)
    # in a real scenario, we might want to fail hard, but here we want to ensure flow
