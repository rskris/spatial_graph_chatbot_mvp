"""
Load the Sierra Madre property graph into Neo4j.
"""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
from neo4j import GraphDatabase
from tqdm import tqdm

import config

BATCH_SIZE = 500


def clean_props(row: dict) -> dict:
    return {
        k: v for k, v in row.items()
        if v is not None and not (isinstance(v, float) and math.isnan(v))
    }


def create_constraints(session):
    for label in ("Building", "Address", "Place", "Division", "Parcel"):
        session.run(
            f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label}) REQUIRE n.node_id IS UNIQUE"
        )


def load_nodes(session, nodes_df: pd.DataFrame):
    for node_type, group in nodes_df.groupby("node_type"):
        records = [clean_props(r) for r in group.to_dict("records")]
        total = len(records)
        print(f"  Loading {total:,} {node_type} nodes...")
        for i in tqdm(range(0, total, BATCH_SIZE), desc=node_type):
            batch = records[i : i + BATCH_SIZE]
            session.run(
                f"""
                UNWIND $batch AS props
                MERGE (n:{node_type} {{node_id: props.node_id}})
                SET n += props
                """,
                batch=batch,
            )


def load_edges(session, edges_df: pd.DataFrame):
    for rel_type, group in edges_df.groupby("rel_type"):
        records = [clean_props(r) for r in group.to_dict("records")]
        total = len(records)
        print(f"  Loading {total:,} {rel_type} edges...")
        for i in tqdm(range(0, total, BATCH_SIZE), desc=rel_type):
            batch = records[i : i + BATCH_SIZE]
            session.run(
                f"""
                UNWIND $batch AS e
                MATCH (src {{node_id: e.src_id}})
                MATCH (dst {{node_id: e.dst_id}})
                MERGE (src)-[r:{rel_type}]->(dst)
                SET r += e
                """,
                batch=batch,
            )


def main():
    nodes_path = Path(config.DATA_DIR) / "nodes.parquet"
    edges_path = Path(config.DATA_DIR) / "edges.parquet"

    if not nodes_path.exists():
        print("ERROR: Run 02_build_graph.py first.")
        return

    nodes_df = pd.read_parquet(nodes_path)
    edges_df = pd.read_parquet(edges_path)

    driver = GraphDatabase.driver(
        config.NEO4J_URI,
        auth=(config.NEO4J_USER, config.NEO4J_PASSWORD),
    )

    with driver.session() as session:
        print("Creating constraints...")
        create_constraints(session)
        print("\nLoading nodes...")
        load_nodes(session, nodes_df)
        print("\nLoading edges...")
        load_edges(session, edges_df)

    driver.close()
    print("\nNeo4j load complete.")


if __name__ == "__main__":
    main()
