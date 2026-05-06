# Sierra Madre, CA bounding box (WGS84)
BBOX = {
    "xmin": -118.08,
    "ymin": 34.14,
    "xmax": -118.02,
    "ymax": 34.20,
}

# Overture feature types to download
OVERTURE_TYPES = ["building", "address", "place", "division", "division_area"]

DATA_DIR = "data"

# Spatial join thresholds
ADDRESS_TO_BUILDING_MAX_METERS = 50   # snap address to nearest building within 50m
PLACE_TO_BUILDING_MAX_METERS = 5      # place centroid inside or within 5m of building

# Neo4j connection (update with your credentials)
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password"

# Graph export paths
GRAPHML_PATH = "data/sierra_madre_property_graph.graphml"
NODES_PARQUET = "data/nodes.parquet"
EDGES_PARQUET = "data/edges.parquet"
