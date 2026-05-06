"""
Build a property graph from Overture Maps data for Sierra Madre, CA.

Graph model:
  NODE TYPES: Building, Address, Place, Division
  EDGE TYPES: HAS_ADDRESS, IN_BUILDING, IN_DIVISION, PART_OF

Outputs:
  data/nodes.parquet
  data/edges.parquet
  data/sierra_madre_property_graph.graphml
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import geopandas as gpd
import networkx as nx
import pandas as pd
from shapely.geometry import Point
from tqdm import tqdm

import config

warnings.filterwarnings("ignore", message=".*initial implementation.*")


def _safe_str(val) -> str | None:
    import numpy as np
    if val is None:
        return None
    if isinstance(val, float) and pd.isna(val):
        return None
    if isinstance(val, np.ndarray):
        val = val.tolist()
    if isinstance(val, (dict, list)):
        try:
            return json.dumps(val, ensure_ascii=False, default=str)
        except Exception:
            return str(val)
    return str(val)


def _primary_name(names) -> str | None:
    if names is None:
        return None
    if isinstance(names, dict):
        primary = names.get("primary")
        if primary:
            return str(primary)
        common = names.get("common", [])
        if common and isinstance(common, list) and len(common) > 0:
            return str(common[0].get("value", ""))
    return None


def _categories_str(cats) -> str | None:
    if cats is None:
        return None
    if isinstance(cats, dict):
        primary = cats.get("primary")
        return str(primary) if primary else None
    return str(cats)


def load_parquet(name: str) -> gpd.GeoDataFrame | None:
    path = Path(config.DATA_DIR) / f"{name}.parquet"
    if not path.exists():
        print(f"  [warn] {path} not found — skipping")
        return None
    gdf = gpd.read_parquet(path)
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")
    return gdf


def build_building_nodes(gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    rows = []
    for _, row in tqdm(gdf.iterrows(), total=len(gdf), desc="Buildings"):
        centroid = row.geometry.centroid if row.geometry else None
        rows.append({
            "node_id": row["id"],
            "node_type": "Building",
            "geometry_wkt": row.geometry.wkt if row.geometry else None,
            "centroid_wkt": centroid.wkt if centroid else None,
            "lon": centroid.x if centroid else None,
            "lat": centroid.y if centroid else None,
            "name": _primary_name(row.get("names")),
            "subtype": _safe_str(row.get("subtype")),
            "class": _safe_str(row.get("class")),
            "height": row.get("height"),
            "num_floors": row.get("num_floors"),
        })
    return pd.DataFrame(rows)


def build_address_nodes(gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    rows = []
    for _, row in tqdm(gdf.iterrows(), total=len(gdf), desc="Addresses"):
        geom = row.geometry
        rows.append({
            "node_id": row["id"],
            "node_type": "Address",
            "geometry_wkt": geom.wkt if geom else None,
            "centroid_wkt": geom.wkt if geom else None,
            "lon": geom.x if geom else None,
            "lat": geom.y if geom else None,
            "number": _safe_str(row.get("number")),
            "street": _safe_str(row.get("street")),
            "postcode": _safe_str(row.get("postcode")),
        })
    return pd.DataFrame(rows)


def build_place_nodes(gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    rows = []
    for _, row in tqdm(gdf.iterrows(), total=len(gdf), desc="Places"):
        geom = row.geometry
        rows.append({
            "node_id": row["id"],
            "node_type": "Place",
            "geometry_wkt": geom.wkt if geom else None,
            "centroid_wkt": geom.wkt if geom else None,
            "lon": geom.x if geom else None,
            "lat": geom.y if geom else None,
            "name": _primary_name(row.get("names")),
            "category": _categories_str(row.get("categories")),
        })
    return pd.DataFrame(rows)


def build_division_nodes(gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    rows = []
    for _, row in tqdm(gdf.iterrows(), total=len(gdf), desc="Divisions"):
        geom = row.geometry
        centroid = geom.centroid if geom else None
        rows.append({
            "node_id": row["id"],
            "node_type": "Division",
            "geometry_wkt": geom.wkt if geom else None,
            "centroid_wkt": centroid.wkt if centroid else None,
            "lon": centroid.x if centroid else None,
            "lat": centroid.y if centroid else None,
            "name": _primary_name(row.get("names")),
            "subtype": _safe_str(row.get("subtype")),
        })
    return pd.DataFrame(rows)


def _to_metric_crs(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    return gdf.to_crs("EPSG:3310")  # CA Albers


def edges_place_has_address(places_gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    rows = []
    for _, row in places_gdf.iterrows():
        addrs = row.get("addresses")
        if not addrs:
            continue
        if isinstance(addrs, list):
            for a in addrs:
                if isinstance(a, dict):
                    street = a.get("street", "")
                    number = a.get("freeform", a.get("number", ""))
                    synth_id = f"addr::{row['id']}::{street}::{number}"
                    rows.append({
                        "src_id": row["id"],
                        "dst_id": synth_id,
                        "rel_type": "HAS_ADDRESS",
                    })
    return pd.DataFrame(rows)


def edges_building_has_address(
    buildings_gdf: gpd.GeoDataFrame,
    addresses_gdf: gpd.GeoDataFrame,
    max_meters: float = config.ADDRESS_TO_BUILDING_MAX_METERS,
) -> pd.DataFrame:
    b_metric = _to_metric_crs(buildings_gdf[["id", "geometry"]].copy())
    b_metric["centroid"] = b_metric.geometry.centroid
    b_pts = b_metric.set_geometry("centroid")[["id", "centroid"]].rename(
        columns={"id": "building_id"}
    )
    a_metric = _to_metric_crs(addresses_gdf[["id", "geometry"]].copy())
    joined = gpd.sjoin_nearest(
        a_metric,
        b_pts.set_geometry("centroid"),
        how="left",
        max_distance=max_meters,
        distance_col="dist_m",
    )
    joined = joined.dropna(subset=["building_id"])
    rows = []
    for _, r in joined.iterrows():
        rows.append({
            "src_id": r["building_id"],
            "dst_id": r["id"],
            "rel_type": "HAS_ADDRESS",
            "dist_m": round(r["dist_m"], 2),
        })
    return pd.DataFrame(rows)


def edges_place_in_building(
    places_gdf: gpd.GeoDataFrame,
    buildings_gdf: gpd.GeoDataFrame,
    max_meters: float = config.PLACE_TO_BUILDING_MAX_METERS,
) -> pd.DataFrame:
    p_metric = _to_metric_crs(places_gdf[["id", "geometry"]].copy())
    b_metric = _to_metric_crs(buildings_gdf[["id", "geometry"]].copy())
    contained = gpd.sjoin(
        p_metric, b_metric.rename(columns={"id": "building_id"}),
        how="left", predicate="within"
    )
    contained = contained.dropna(subset=["building_id"])
    rows = [
        {"src_id": r["id"], "dst_id": r["building_id"],
         "rel_type": "IN_BUILDING", "method": "contains"}
        for _, r in contained.iterrows()
    ]
    unmatched_ids = set(places_gdf["id"]) - set(contained["id"])
    if unmatched_ids:
        p_unmatched = p_metric[p_metric["id"].isin(unmatched_ids)]
        b_centroids = b_metric.copy()
        b_centroids["geometry"] = b_centroids.geometry.centroid
        nearby = gpd.sjoin_nearest(
            p_unmatched, b_centroids.rename(columns={"id": "building_id"}),
            how="left", max_distance=max_meters, distance_col="dist_m"
        )
        nearby = nearby.dropna(subset=["building_id"])
        for _, r in nearby.iterrows():
            rows.append({
                "src_id": r["id"],
                "dst_id": r["building_id"],
                "rel_type": "IN_BUILDING",
                "method": "nearest",
                "dist_m": round(r["dist_m"], 2),
            })
    return pd.DataFrame(rows)


def edges_in_division(
    points_gdf: gpd.GeoDataFrame,
    division_areas_gdf: gpd.GeoDataFrame,
    src_type: str,
) -> pd.DataFrame:
    pts = _to_metric_crs(points_gdf[["id", "geometry"]].copy())
    pts["geometry"] = pts.geometry.centroid if src_type == "Building" else pts.geometry
    divs = _to_metric_crs(
        division_areas_gdf[["division_id", "geometry"]].rename(
            columns={"division_id": "div_id"}
        ).copy()
    )
    joined = gpd.sjoin(pts, divs, how="left", predicate="within")
    joined = joined.dropna(subset=["div_id"])
    rows = []
    for _, r in joined.iterrows():
        rows.append({
            "src_id": r["id"],
            "dst_id": r["div_id"],
            "rel_type": "IN_DIVISION",
            "src_type": src_type,
        })
    return pd.DataFrame(rows)


def edges_division_hierarchy(divisions_gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    rows = []
    for _, row in divisions_gdf.iterrows():
        parent = row.get("parent_division_id")
        if parent and not pd.isna(parent):
            rows.append({
                "src_id": row["id"],
                "dst_id": str(parent),
                "rel_type": "PART_OF",
            })
    return pd.DataFrame(rows)


def build_networkx_graph(nodes_df: pd.DataFrame, edges_df: pd.DataFrame) -> nx.MultiDiGraph:
    G = nx.MultiDiGraph()
    for _, row in tqdm(nodes_df.iterrows(), total=len(nodes_df), desc="Graph Nodes"):
        attrs = {k: v for k, v in row.items()
                 if k != "node_id" and v is not None and not (isinstance(v, float) and pd.isna(v))}
        G.add_node(row["node_id"], **attrs)
    for _, row in tqdm(edges_df.iterrows(), total=len(edges_df), desc="Graph Edges"):
        attrs = {k: v for k, v in row.items()
                 if k not in ("src_id", "dst_id") and v is not None
                 and not (isinstance(v, float) and pd.isna(v))}
        G.add_edge(row["src_id"], row["dst_id"], **attrs)
    return G


def main():
    print("=== Sierra Madre Property Graph Builder ===\n")
    buildings_gdf = load_parquet("building")
    addresses_gdf = load_parquet("address")
    places_gdf = load_parquet("place")
    divisions_gdf = load_parquet("division")
    div_areas_gdf = load_parquet("division_area")

    node_frames = []
    if buildings_gdf is not None: node_frames.append(build_building_nodes(buildings_gdf))
    if addresses_gdf is not None: node_frames.append(build_address_nodes(addresses_gdf))
    if places_gdf is not None: node_frames.append(build_place_nodes(places_gdf))
    if divisions_gdf is not None: node_frames.append(build_division_nodes(divisions_gdf))

    nodes_df = pd.concat(node_frames, ignore_index=True)
    
    edge_frames = []
    if places_gdf is not None and addresses_gdf is not None:
        edge_frames.append(edges_place_has_address(places_gdf))
    if buildings_gdf is not None and addresses_gdf is not None:
        edge_frames.append(edges_building_has_address(buildings_gdf, addresses_gdf))
    if places_gdf is not None and buildings_gdf is not None:
        edge_frames.append(edges_place_in_building(places_gdf, buildings_gdf))
    if buildings_gdf is not None and div_areas_gdf is not None:
        edge_frames.append(edges_in_division(buildings_gdf, div_areas_gdf, "Building"))
    if addresses_gdf is not None and div_areas_gdf is not None:
        edge_frames.append(edges_in_division(addresses_gdf, div_areas_gdf, "Address"))
    if divisions_gdf is not None:
        edge_frames.append(edges_division_hierarchy(divisions_gdf))

    edges_df = pd.concat(edge_frames, ignore_index=True) if edge_frames else pd.DataFrame()

    out = Path(config.DATA_DIR)
    nodes_df.to_parquet(out / "nodes.parquet", index=False)
    edges_df.to_parquet(out / "edges.parquet", index=False)

    G = build_networkx_graph(nodes_df, edges_df)
    nx.write_graphml(G, config.GRAPHML_PATH)
    print(f"\nDone. GraphML saved to {config.GRAPHML_PATH}")


if __name__ == "__main__":
    main()
