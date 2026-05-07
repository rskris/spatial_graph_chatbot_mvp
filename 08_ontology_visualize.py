import networkx as nx
import matplotlib.pyplot as plt
from pathlib import Path

# Configuration
OUTPUT_PATH = Path("data/ontology_graph.png")

# Styling
TYPE_COLORS = {
    "Building": "#fb923c",  # Orange
    "Address": "#34d399",   # Emerald
    "Place": "#c084fc",     # Purple
    "Parcel": "#818cf8",    # Indigo
    "Division": "#fb7185",  # Rose
}

def generate_ontology_visualization():
    print("Generating ontology (schema) visualization...")
    
    # Create NetworkX graph for the schema
    G = nx.MultiDiGraph()
    
    # Define the nodes (Entity Types)
    nodes = [
        ("Building", "Structure with geometry\nand classification"),
        ("Address", "Point location with\nstreet & number"),
        ("Place", "Point of interest or\nbusiness entity"),
        ("Parcel", "Land property boundary\nwith assessor data"),
        ("Division", "Administrative area\n(City, County, etc.)")
    ]
    
    for n, desc in nodes:
        G.add_node(n, label=n, description=desc, color=TYPE_COLORS[n])
        
    # Define the relationships (Edges)
    edges = [
        ("Building", "Address", "HAS_ADDRESS"),
        ("Place", "Building", "IN_BUILDING"),
        ("Building", "Division", "IN_DIVISION"),
        ("Division", "Division", "PART_OF"),
        ("Building", "Parcel", "ON_PARCEL"),
        ("Address", "Parcel", "ON_PARCEL"),
        ("Place", "Parcel", "ON_PARCEL"),
    ]
    
    for src, dst, rel in edges:
        G.add_edge(src, dst, label=rel)

    # Visualization
    plt.switch_backend('Agg')
    plt.figure(figsize=(12, 10), facecolor="#0f172a")
    ax = plt.gca()
    ax.set_facecolor("#0f172a")
    
    # Manual positioning for a clean "global" look
    pos = {
        "Place": (0, 2),
        "Building": (2, 2),
        "Address": (4, 2),
        "Parcel": (2, 0),
        "Division": (2, 4)
    }
    
    # Draw nodes
    node_colors = [G.nodes[n]['color'] for n in G.nodes()]
    nx.draw_networkx_nodes(G, pos, node_size=5000, node_color=node_colors, alpha=0.9, ax=ax)
    
    # Draw labels (Type names)
    labels = {n: n for n in G.nodes()}
    nx.draw_networkx_labels(G, pos, labels, font_size=12, font_color="#0f172a", font_weight="bold", ax=ax)
    
    # Draw descriptions (below names)
    desc_pos = {n: (x, y-0.35) for n, (x, y) in pos.items()}
    descriptions = {n: G.nodes[n]['description'] for n in G.nodes()}
    nx.draw_networkx_labels(G, desc_pos, descriptions, font_size=9, font_color="#cbd5e1", ax=ax)
    
    # Draw edges with curves to avoid overlap
    for i, (u, v, k, d) in enumerate(G.edges(data=True, keys=True)):
        rad = 0.1 * (k + 1)
        if u == v: # Self-loop for Division PART_OF
            rad = 0.3
            nx.draw_networkx_edges(G, pos, edgelist=[(u, v)], connectionstyle=f"arc3,rad={rad}", 
                                   arrowstyle='->', arrowsize=20, edge_color="#6366f1", width=2, ax=ax)
        else:
            nx.draw_networkx_edges(G, pos, edgelist=[(u, v)], connectionstyle=f"arc3,rad={rad}", 
                                   arrowstyle='->', arrowsize=20, edge_color="#475569", width=2, ax=ax)

    # Edge labels
    edge_labels = {}
    for u, v, k, d in G.edges(data=True, keys=True):
        edge_labels[(u, v, k)] = d['label']
        
    # We use a custom label drawer for better placement on curved edges
    for (u, v, k), label in edge_labels.items():
        if u == v:
            x, y = pos[u]
            ax.text(x, y+0.5, label, color="#818cf8", fontsize=10, ha='center', fontweight='bold')
        else:
            # Simple midpoint for now, though curved edges need more care
            x = (pos[u][0] + pos[v][0]) / 2
            y = (pos[u][1] + pos[v][1]) / 2
            # Offset slightly based on k to avoid collision
            y_off = 0.15 if k == 0 else -0.15
            ax.text(x, y + y_off, label, color="#94a3b8", fontsize=10, ha='center', fontweight='bold', 
                    bbox=dict(facecolor='#1e293b', alpha=0.8, edgecolor='none', boxstyle='round,pad=0.2'))

    plt.title("Sierra Madre Property Graph: Global Ontology (Schema)", color="#f1f5f9", size=18, pad=30)
    plt.axis('off')
    
    # Add a note about the data source
    plt.figtext(0.5, 0.05, "Data Model: Overture Maps (Buildings, Places, Addresses, Divisions) + LA County Assessor (Parcels)", 
                ha="center", color="#475569", fontsize=10)
    
    plt.tight_layout()
    plt.savefig(OUTPUT_PATH, facecolor="#0f172a")
    print(f"Ontology visualization saved to {OUTPUT_PATH}")

if __name__ == "__main__":
    generate_ontology_visualization()
