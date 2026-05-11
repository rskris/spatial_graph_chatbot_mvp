# NOTE: This script now handles processing local GeoJSON files and applying bounding box filters.
# The core function is now a generalized loader, decoupling it from the original LA County MapServer API endpoint.

from __future__ import annotations

import geopandas as gpd
import pandas as pd
import requests # Keep for potential future API calls
from shapely.geometry import shape
from tqdm import tqdm
import config
from pathlib import Path


# Fields are now passed dynamically, but we keep a placeholder/example schema structure
DEFAULT_FIELDS = [
    "OBJECTID", "APN", "Situs1", "Situs2", "LandUse", "Acreage",
    "YearBuilt", "Bedrooms", "Bathrooms", "NetSecVal", "SqFootage"
]

PAGE_SIZE = 1000
OUT_CRS = "EPSG:4326"

def load_parcels(file_path: str, schema: list[str], bbox: dict) -> gpd.GeoDataFrame:
    """
    Loads parcels from a specified GeoJSON file and filters them using the given bounding box.

    Args:
        file_path (str): Absolute path to the input GeoJSON file.
        schema (list[str]): List of attributes/fields to keep from the source data.
        bbox (dict): Dictionary containing the geographical bounds {'xmin', 'ymin', 'xmax', 'ymax'}.

    Returns:
        gpd.GeoDataFrame: A GeoDataFrame containing only parcels within the bounding box,
                           with selected schema attributes.
    """
    print(f"Processing file: {file_path}...")
    try:
        # 1. Load the full GeoJSON dataset first
        gdf = gpd.read_file(file_path)
    except Exception as e:
        raise IOError(f"Failed to read GeoJSON file at {file_path}: {e}")

    print("Filtering by bounding box...")
    # 2. Filter the data using the provided bounding box (CRS 4326 assumed)
    # We check for geometry intersection with an envelope defined by the user's BBOX
    envelope = shape({'type': 'Polygon', 'coordinates': [[
        [bbox['xmin'], bbox['ymin']], [bbox['xmax'], bbox['ymin']], [bbox['xmax'], bbox['ymax']], [bbox['xmin'], bbox['ymax']]]
    ]})

    # Filter to keep only geometries that intersect the search envelope
    filtered_gdf = gdf[gdf.geometry.apply(lambda geom: geom.intersects(envelope))].copy()

    if filtered_gdf.empty:
        print("Warning: No parcels found within the specified bounding box.")
        return gpd.GeoDataFrame(columns=[f'geometry'] + schema)

    # 3. Select and rename columns based on the target schema
    available_cols = list(filtered_gdf.columns)
    selected_schema = [col for col in schema if col in available_cols]

    if not selected_schema:
        print("Error: None of the specified schema fields were found in the GeoJSON file.")
        return gpd.GeoDataFrame(columns=[f'geometry'] + schema)

    # Select only the necessary columns, including geometry
    final_gdf = filtered_gdf[selected_schema + ['geometry']].copy()

    print(f"Successfully loaded {len(final_gdf):,} parcels for Goleta.")
    return final_gdf


def main():
    """Main entry point to process and save the local GeoJSON file."""
    # --- CONFIGURATION FOR GOLETA DATA INGESTION ---
    INPUT_FILE = "/Users/rskris/Downloads/sbcounty_parcels.geojson" # Hardcoded for current task context
    OUTPUT_PATH = Path(config.DATA_DIR) / "goleta_parcels.parquet"

    # Schema and BBOX defined by user input and analysis
    TARGET_SCHEMA = [
        "OBJECTID", "APN", "Situs1", "Situs2", "LandUse", "Acreage",
        "YearBuilt", "Bedrooms", "Bathrooms", "NetSecVal", "SqFootage"
    ]
    GOLETA_BBOX = {
        'xmin': -119.9195, # West Longitude
        'ymin': 34.4001,  # South Latitude
        'xmax': -119.7994, # East Longitude
        'ymax': 34.4567   # North Latitude
    }
    # --- END CONFIGURATION ---

    if OUTPUT_PATH.exists():
        print(f"[skip] {OUTPUT_PATH} already exists")
        return

    try:
        goleta_gdf = load_parcels(INPUT_FILE, TARGET_SCHEMA, GOLETA_BBOX)

        # Save the filtered data to a new parquet file for consistency with existing workflow
        print(f"Saving filtered GeoDataFrame to {OUTPUT_PATH}...")
        goleta_gdf.to_parquet(OUTPUT_PATH, index=False)
        print("Data loading and filtering complete.")

    except Exception as e:
        print(f"A critical error occurred during parcel data processing: {e}")

if __name__ == "__main__":
    # This ensures the main function runs when executed directly
    main()

if __name__ == "__main__":
    main()
