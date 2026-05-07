# Sierra Madre Property Graph

This project builds a property graph for Sierra Madre, CA using Overture Maps data, integrating spatial logic and parcel boundaries to power a sophisticated reasoning engine.

## 🤖 Sierra Madre Geospatial & Graph Reasoning Chatbot

The project includes an intelligent chatbot that combines spatial intelligence with graph traversal to answer complex questions about buildings, places, parcels, and addresses in Sierra Madre.

### Chatbot Capabilities

The chatbot understands the Sierra Madre environment as a **connected spatial graph** and can navigate relationships to answer queries:

- **Entity Information Lookup:** Get full details on any building, place, or address (e.g., *"Tell me about Sierra Madre City Hall"*).
- **Relationship & Content Discovery:** Query what entities are contained within or associated with others (e.g., *"What businesses are in 600 North Rosemead Boulevard?"*).
- **Parcel & Ownership Reasoning:** Connect physical structures to LA County Assessor data (e.g., *"What else is on the same parcel as 232 West Sierra Madre Boulevard?"*).
- **Advanced Proximity Searches:** Perform meter-accurate searches around any graph entity using high-precision metric projections (e.g., *"How many coffee shops are within 500m of City Hall?"*).
- **Address & Name Resolution:** Supports fuzzy matching and synonyms to handle variations and typos in user queries.

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

5.  **Run the Chatbot**:
    - **Web Interface (Recommended):**
      ```bash
      python app.py
      ```
      Then open [http://localhost:5001](http://localhost:5001) in your browser.
    - **CLI Version:**
      ```bash
      python chatbot.py
      ```

## 📊 Visualizations

The project provides an **Interactive Geospatial Map** to explore the property graph:

1.  Run the visualizer:
    ```bash
    python 06_visualize.py
    ```
2.  Open the generated `data/property_graph_map.html` in your browser. Clicking on any feature reveals its property records and connected entities.

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
