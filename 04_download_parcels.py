"""
Download Sierra Madre parcels from the LA County Assessor MapServer.

Source: LA County Enterprise GIS (eGIS)
Endpoint: https://public.gis.lacounty.gov/public/rest/services/LACounty_Cache/LACounty_Parcel/MapServer/0

Uses the Sierra Madre bounding box from config.py.
Outputs data/parcels.parquet.
"""

from __future__ import annotations

import time
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests
from shapely.geometry import shape
from tqdm import tqdm

import config

BASE_URL = (
    "https://public.gis.lacounty.gov/public/rest/services"
    "/LACounty_Cache/LACounty_Parcel/MapServer/0/query"
)

# Representative fields (LA County schema differs from SB County)
FIELDS = [
    "OBJECTID", "AIN", "APN", "SitusAddress", "SitusCity", "SitusZIP",
    "UseDescription", "YearBuilt1", "Bedrooms1", "Bathrooms1", "SQFTmain1",
    "Roll_LandValue", "Roll_ImpValue", "Roll_HomeOwnersExemp",
]

PAGE_SIZE = 1000
OUT_CRS = "EPSG:4326"

def get_total_count(bbox: dict) -> int:
    params = {
        "where": "1=1",
        "geometry": f"{bbox['xmin']},{bbox['ymin']},{bbox['xmax']},{bbox['ymax']}",
        "geometryType": "esriGeometryEnvelope",
        "spatialRel": "esriSpatialRelIntersects",
        "inSR": "4326",
        "returnCountOnly": "true",
        "f": "json",
    }
    resp = requests.get(BASE_URL, params=params, timeout=60)
    resp.raise_for_status()
    return resp.json().get("count", 0)

def fetch_page(bbox: dict, offset: int) -> list[dict]:
    params = {
        "where": "1=1",
        "geometry": f"{bbox['xmin']},{bbox['ymin']},{bbox['xmax']},{bbox['ymax']}",
        "geometryType": "esriGeometryEnvelope",
        "spatialRel": "esriSpatialRelIntersects",
        "inSR": "4326",
        "outFields": ",".join(FIELDS),
        "returnGeometry": "true",
        "outSR": "4326",
        "resultOffset": offset,
        "resultRecordCount": PAGE_SIZE,
        "f": "geojson",
    }
    for attempt in range(4):
        try:
            resp = requests.get(BASE_URL, params=params, timeout=120)
            resp.raise_for_status()
            data = resp.json()
            return data.get("features", [])
        except Exception as e:
            if attempt == 3:
                print(f"Failed to fetch offset {offset}: {e}")
                raise
            time.sleep(2 ** attempt)
    return []

def main():
    out_path = Path(config.DATA_DIR) / "parcels.parquet"
    if out_path.exists():
        print(f"[skip] {out_path} already exists")
        return

    print(f"Fetching total parcel count for BBOX {config.BBOX}...")
    total_count = get_total_count(config.BBOX)
    print(f"  Estimated total: {total_count:,} parcels")

    all_features = []
    print(f"Downloading in pages of {PAGE_SIZE}...")
    for offset in tqdm(range(0, total_count + PAGE_SIZE, PAGE_SIZE)):
        features = fetch_page(config.BBOX, offset)
        if not features:
            break
        all_features.extend(features)
        time.sleep(0.1)

    print(f"  Downloaded {len(all_features):,} features total")

    print("Building GeoDataFrame...")
    rows = []
    geometries = []
    for feat in all_features:
        props = feat.get("properties") or {}
        geom_raw = feat.get("geometry")
        if geom_raw:
            try:
                geometries.append(shape(geom_raw))
            except Exception:
                geometries.append(None)
        else:
            geometries.append(None)
        rows.append(props)

    df = pd.DataFrame(rows)
    gdf = gpd.GeoDataFrame(df, geometry=geometries, crs=OUT_CRS)

    # Drop rows with null geometry
    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].reset_index(drop=True)

    print(f"  Valid geometries: {len(gdf):,}")
    print(f"  Saving to {out_path}...")
    gdf.to_parquet(out_path, index=False)
    print("Done.")

if __name__ == "__main__":
    main()
