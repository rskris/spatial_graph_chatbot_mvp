# Sierra Madre Property Graph

This project builds a property graph for Sierra Madre, CA using Overture Maps data.

## Prerequisites

1.  Python 3.10+
2.  Neo4j (running locally or accessible via URI in `config.py`)
3.  Overture Maps CLI (`pip install overturemaps`)

## Setup

1.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

2.  Update `config.py` with your Neo4j credentials if they differ from the defaults.

## Usage

1.  **Download Data**:
    ```bash
    python 01_download.py
    ```
    This downloads Buildings, Addresses, Places, and Divisions for the Sierra Madre bounding box.

2.  **Build Graph**:
    ```bash
    python 02_build_graph.py
    ```
    This processes the raw data, performs spatial joins, and generates `nodes.parquet`, `edges.parquet`, and a GraphML file.

3.  **Load into Neo4j**:
    ```bash
    python 03_load_neo4j.py
    ```
    This loads the nodes and edges into your Neo4j database.

4.  **Integrate Parcels (Optional)**:
    - Download parcels: `python 04_download_parcels.py`
    - Integrate parcels: `python 05_integrate_parcels.py`
    - Re-run `python 03_load_neo4j.py` to load parcel nodes and `ON_PARCEL` edges.

## Data Model

-   **Nodes**: `Building`, `Address`, `Place`, `Division`, `Parcel`
-   **Edges**:
    -   `(Building)-[:HAS_ADDRESS]->(Address)`
    -   `(Place)-[:IN_BUILDING]->(Building)`
    -   `(Building)-[:IN_DIVISION]->(Division)`
    -   `(Division)-[:PART_OF]->(Division)`
    -   `(Building)-[:ON_PARCEL]->(Parcel)`
    -   `(Address)-[:ON_PARCEL]->(Parcel)`
    -   `(Place)-[:ON_PARCEL]->(Parcel)`
