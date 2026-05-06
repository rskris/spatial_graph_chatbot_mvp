"""
Integrate Sierra Madre parcel data into the property graph.

Adds:
  NODE: Parcel  — APN (AIN), address, use, value, year built, etc.
  EDGE: (Building)-[:ON_PARCEL]->(Parcel)
  EDGE: (Address)-[:ON_PARCEL]->(Parcel)
  EDGE: (Place)-[:ON_PARCEL]->(Parcel)

Updates data/nodes.parquet and data/edges.parquet in-place.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import geopandas as gpd
import pandas as pd
from tqdm import tqdm

import config

warnings.filterwarnings("ignore")

METRIC_CRS = "EPSG:3310"  # CA Albers


def build_parcel_nodes(gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    rows = []
    for _, row in tqdm(gdf.iterrows(), total=len(gdf), desc="Parcel nodes"):
        centroid = row.geometry.centroid if row.geometry else None
        # Map LA County fields to a generic schema
        rows.append({
            "node_id": f"parcel::{row.get('AIN', row.get('OBJECTID', ''))}",
            "node_type": "Parcel",
            "geometry_wkt": row.geometry.wkt if row.geometry else None,
            "centroid_wkt": centroid.wkt if centroid else None,
            "lon": centroid.x if centroid else None,
            "lat": centroid.y if centroid else None,
            "apn": str(row.get("AIN", "") or ""),
            "situs_address": str(row.get("SitusAddress", "") or ""),
            "land_use": str(row.get("UseDescription", "") or ""),
            "year_built": str(row.get("YearBuilt1", "") or ""),
            "bedrooms": row.get("Bedrooms1"),
            "bathrooms": row.get("Bathrooms1"),
            "sq_footage": row.get("SQFTmain1"),
            "land_value": row.get("Roll_LandValue"),
            "imp_value": row.get("Roll_ImpValue"),
            "home_owner_ex": row.get("Roll_HomeOwnersExemp"),
        })
    return pd.DataFrame(rows)


def _to_metric(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    return gdf.to_crs(METRIC_CRS)


def edges_point_in_parcel(
    points_gdf: gpd.GeoDataFrame,
    parcels_gdf: gpd.GeoDataFrame,
    src_type: str,
) -> pd.DataFrame:
    pts = _to_metric(points_gdf[["id", "geometry"]].copy())
    if src_type == "Building":
        pts["geometry"] = pts.geometry.centroid

    pcls = _to_metric(parcels_gdf[["parcel_node_id", "geometry"]].copy())

    joined = gpd.sjoin(
        pts,
        pcls.rename(columns={"parcel_node_id": "dst_id"}),
        how="left",
        predicate="within",
    )
    joined = joined.dropna(subset=["dst_id"])

    rows = []
    for _, r in joined.iterrows():
        rows.append({
            "src_id": r["id"],
            "dst_id": r["dst_id"],
            "rel_type": "ON_PARCEL",
            "src_type": src_type,
        })
    return pd.DataFrame(rows)


def main():
    parcel_path = Path(config.DATA_DIR) / "parcels.parquet"
    nodes_path = Path(config.DATA_DIR) / "nodes.parquet"
    edges_path = Path(config.DATA_DIR) / "edges.parquet"

    if not parcel_path.exists():
        print("ERROR: Run 04_download_parcels.py first.")
        return
    if not nodes_path.exists():
        print("ERROR: Run 02_build_graph.py first.")
        return

    print("=== Sierra Madre Parcel Integration ===\n")

    print("Loading parcel data...")
    parcels_gdf = gpd.read_parquet(parcel_path)
    if parcels_gdf.crs is None:
        parcels_gdf = parcels_gdf.set_crs("EPSG:4326")
    
    parcels_gdf["parcel_node_id"] = parcels_gdf.apply(
        lambda r: f"parcel::{r.get('AIN', r.get('OBJECTID', ''))}", axis=1
    )

    print("\nBuilding Parcel nodes...")
    parcel_nodes = build_parcel_nodes(parcels_gdf)

    print("\nLoading existing nodes...")
    existing_nodes = pd.read_parquet(nodes_path)

    def nodes_as_gdf(ntype: str) -> gpd.GeoDataFrame | None:
        subset = existing_nodes[existing_nodes["node_type"] == ntype].copy()
        if subset.empty:
            return None
        from shapely import wkt as swkt
        subset["geometry"] = subset["centroid_wkt"].apply(swkt.loads)
        gdf = gpd.GeoDataFrame(subset, geometry="geometry", crs="EPSG:4326")
        gdf = gdf.rename(columns={"node_id": "id"})
        return gdf

    buildings_gdf = nodes_as_gdf("Building")
    addresses_gdf = nodes_as_gdf("Address")
    places_gdf = nodes_as_gdf("Place")

    print("\nBuilding ON_PARCEL edges...")
    edge_frames = []
    if buildings_gdf is not None:
        edge_frames.append(edges_point_in_parcel(buildings_gdf, parcels_gdf, "Building"))
    if addresses_gdf is not None:
        edge_frames.append(edges_point_in_parcel(addresses_gdf, parcels_gdf, "Address"))
    if places_gdf is not None:
        edge_frames.append(edges_point_in_parcel(places_gdf, parcels_gdf, "Place"))

    new_edges = pd.concat(edge_frames, ignore_index=True) if edge_frames else pd.DataFrame()

    print("\nPersisting updated node/edge tables...")
    updated_nodes = pd.concat([existing_nodes, parcel_nodes], ignore_index=True)
    updated_nodes.to_parquet(nodes_path, index=False)

    existing_edges = pd.read_parquet(edges_path)
    updated_edges = pd.concat([existing_edges, new_edges], ignore_index=True)
    updated_edges.to_parquet(edges_path, index=False)

    print("Done.")


if __name__ == "__main__":
    main()
