import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
from pathlib import Path
import random

# Configuration
NODES_PATH = Path("data/nodes.parquet")
EDGES_PATH = Path("data/edges.parquet")
OUTPUT_PATH = Path("data/knowledge_graph.png")

# Styling
TYPE_COLORS = {
    "Building": "#fb923c",  # Orange
    "Address": "#34d399",   # Emerald
    "Place": "#c084fc",     # Purple
    "Parcel": "#818cf8",    # Indigo
    "Division": "#fb7185",  # Rose
}

def generate_kg_visualization():
    if not NODES_PATH.exists() or not EDGES_PATH.exists():
        print("Error: nodes.parquet or edges.parquet not found. Run the build scripts first.")
        return

    print("Loading data...")
    nodes_df = pd.read_parquet(NODES_PATH)
    edges_df = pd.read_parquet(EDGES_PATH)

    # We want a representative subgraph that shows all types and their connections
    # Let's pick a few "seed" nodes of each type if possible
    seeds = []
    
    # Try to find Sierra Madre City Hall as a central anchor
    city_hall = nodes_df[nodes_df['name'].str.contains('City Hall', na=False)]
    if not city_hall.empty:
        seeds.extend(city_hall['node_id'].tolist())

    # Add some random nodes of each type to ensure diversity
    for ntype in TYPE_COLORS.keys():
        type_nodes = nodes_df[nodes_df['node_type'] == ntype]
        if not type_nodes.empty:
            sample_size = min(3, len(type_nodes))
            seeds.extend(type_nodes.sample(sample_size)['node_id'].tolist())

    # Find edges connected to these seeds and their neighbors
    # We'll do a 2-hop expansion
    visible_nodes = set(seeds)
    visible_edges = []

    # Hop 1
    hop1_edges = edges_df[edges_df['src_id'].isin(visible_nodes) | edges_df['dst_id'].isin(visible_nodes)]
    visible_edges.extend(hop1_edges.to_dict('records'))
    visible_nodes.update(hop1_edges['src_id'].tolist())
    visible_nodes.update(hop1_edges['dst_id'].tolist())

    # Hop 2 (optional, maybe keep it small to avoid hairball)
    hop2_edges = edges_df[edges_df['src_id'].isin(visible_nodes) | edges_df['dst_id'].isin(visible_nodes)]
    # Filter hop2 to not explode the graph
    hop2_edges = hop2_edges.sample(min(len(hop2_edges), 100))
    visible_edges.extend(hop2_edges.to_dict('records'))
    visible_nodes.update(hop2_edges['src_id'].tolist())
    visible_nodes.update(hop2_edges['dst_id'].tolist())

    # Create NetworkX graph
    G = nx.MultiDiGraph()
    
    # Add nodes with attributes
    subset_nodes = nodes_df[nodes_df['node_id'].isin(visible_nodes)]
    for _, row in subset_nodes.iterrows():
        label = row.get('name') or row.get('apn') or row.get('number') or row['node_id'][:8]
        if row['node_type'] == 'Address' and row.get('street'):
            label = f"{row.get('number', '')} {row.get('street', '')}".strip()
        
        G.add_node(
            row['node_id'], 
            label=label, 
            type=row['node_type'],
            color=TYPE_COLORS.get(row['node_type'], "#94a3b8")
        )

    # Add edges
    for edge in visible_edges:
        if edge['src_id'] in G and edge['dst_id'] in G:
            G.add_edge(edge['src_id'], edge['dst_id'], label=edge['rel_type'])

    # Visualization
    plt.switch_backend('Agg') # Use non-interactive backend
    plt.figure(figsize=(16, 12), facecolor="#0f172a")
    ax = plt.gca()
    ax.set_facecolor("#0f172a")
    
    # Layout
    pos = nx.spring_layout(G, k=0.5, iterations=50, seed=42)
    
    # Draw nodes
    node_colors = [data['color'] for n, data in G.nodes(data=True)]
    nx.draw_networkx_nodes(G, pos, node_size=800, node_color=node_colors, alpha=0.9, ax=ax)
    
    # Draw labels
    labels = {n: data['label'] for n, data in G.nodes(data=True)}
    nx.draw_networkx_labels(G, pos, labels, font_size=8, font_color="#f1f5f9", font_weight="bold", ax=ax)
    
    # Draw edges
    nx.draw_networkx_edges(G, pos, arrowstyle='->', arrowsize=15, edge_color="#334155", alpha=0.5, ax=ax)
    
    # Edge labels
    # Multi-edges can overlap, so we simplify for the static view
    simple_edge_labels = {}
    for u, v, k, d in G.edges(data=True, keys=True):
        simple_edge_labels[(u, v)] = d['label']
    nx.draw_networkx_edge_labels(G, pos, edge_labels=simple_edge_labels, font_size=7, font_color="#94a3b8", alpha=0.7, ax=ax, label_pos=0.5)

    # Legend
    from matplotlib.lines import Line2D
    legend_elements = [Line2D([0], [0], marker='o', color='w', label=t,
                              markerfacecolor=c, markersize=10) for t, c in TYPE_COLORS.items()]
    ax.legend(handles=legend_elements, loc='upper right', facecolor="#1e293b", edgecolor="#334155", labelcolor="#e2e8f0")

    plt.title("Sierra Madre Property Knowledge Graph (Sample View)", color="#f1f5f9", size=20, pad=20)
    plt.axis('off')
    
    plt.tight_layout()
    plt.savefig(OUTPUT_PATH, facecolor="#0f172a")
    print(f"Knowledge graph visualization saved to {OUTPUT_PATH}")

if __name__ == "__main__":
    generate_kg_visualization()
