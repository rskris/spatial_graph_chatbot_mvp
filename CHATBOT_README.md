# Sierra Madre Geospatial & Graph Reasoning Chatbot

This chatbot is a sophisticated reasoning engine for the Sierra Madre Property Graph. It combines spatial intelligence with graph traversal to answer complex questions about buildings, places, parcels, and addresses.

## 🚀 Getting Started

### Web Interface (Recommended)
Launch the interactive web-based chat:
```bash
python app.py
```
Then open [http://localhost:5001](http://localhost:5001) in your browser.

### CLI Version
Run directly in your terminal:
```bash
python chatbot.py
```

---

## 🧠 Core Capabilities

The chatbot understands the Sierra Madre environment as a **connected spatial graph**. It can navigate relationships like `ON_PARCEL`, `IN_BUILDING`, and `HAS_ADDRESS`.

### 1. Entity Information Lookup
Get full details on any building, place, or address.
- **Example:** `"Tell me about Sierra Madre City Hall"`
- **Response:** Returns building class, height, number of floors, associated APN, and its address.

### 2. Relationship & Content Discovery
Query what entities are contained within or associated with others.
- **Example:** `"What businesses are in 600 North Rosemead Boulevard?"`
- **Example:** `"List the places inside the building at 232 W Sierra Madre Blvd"`
- **Logic:** The bot automatically traverses paths like `Building <- IN_BUILDING - Place` or `Building -> HAS_ADDRESS -> Address <- HAS_ADDRESS - Place`.

### 3. Parcel & Ownership Reasoning
Connect physical structures to LA County Assessor data.
- **Example:** `"What parcel is Sierra Madre City Hall on?"`
- **Example:** `"What else is on the same parcel as 232 West Sierra Madre Boulevard?"`
- **Response:** Returns APN, Land Use descriptions, and lists all other buildings/addresses sharing that specific parcel.

### 4. Advanced Proximity Searches
Perform meter-accurate searches around any graph entity.
- **Example:** `"How many coffee shops are within 500m of City Hall?"`
- **Example:** `"Find parks near 232 West Sierra Madre Blvd"`
- **Logic:** Uses CA Albers (EPSG:3310) metric projection for high-precision distance calculation.

### 5. Address & Name Resolution
- **Fuzzy Matching:** Handles typos and variations (e.g., "St" vs "Street", "Blvd" vs "Boulevard").
- **Synonym Support:** Understands "businesses", "places", "inside", "at", and "near" in various sentence structures.

---

## 🛠 Technical Architecture

- **Engine:** Python / Geopandas / Pandas / Shapely.
- **Graph Model:** Adjacency-list based traversal supporting multi-hop paths.
- **Spatial Index:** R-Tree indexed spatial joins for proximity performance.
- **Parsing:** Intent-based regex and fuzzy matching (expandable to LLM-based parsing).
- **Backend:** Flask (serving a Vanilla JS/CSS frontend).

## 📊 Relationship Model
The bot navigates the following core relationships:
- `(Place)-[:IN_BUILDING]->(Building)`
- `(Building)-[:HAS_ADDRESS]->(Address)`
- `(Address)-[:ON_PARCEL]->(Parcel)`
- `(Building)-[:ON_PARCEL]->(Parcel)`
- `(Entity)-[:IN_DIVISION]->(Division)`
