import os
import sys
import re
import difflib
import pandas as pd
import geopandas as gpd
from shapely import wkt
from shapely.geometry import Point
import config

class PropertyGraphChatbot:
    def __init__(self, nodes_parquet=config.NODES_PARQUET, edges_parquet=config.EDGES_PARQUET):
        if not os.path.exists(nodes_parquet):
            raise FileNotFoundError(f"Data file {nodes_parquet} not found.")
            
        print(f"Loading Sierra Madre Spatial Graph...")
        self.nodes_df = pd.read_parquet(nodes_parquet)
        self.edges_df = pd.read_parquet(edges_parquet)
        
        # Build adjacency maps for fast graph traversal
        self.adj_out = {}
        self.adj_in = {}
        for _, row in self.edges_df.iterrows():
            src, dst, rel = row['src_id'], row['dst_id'], row['rel_type']
            self.adj_out.setdefault(src, []).append((dst, rel, row.to_dict()))
            self.adj_in.setdefault(dst, []).append((src, rel, row.to_dict()))

        # Spatial indexing
        self.nodes_gdf = gpd.GeoDataFrame(
            self.nodes_df,
            geometry=self.nodes_df['centroid_wkt'].apply(wkt.loads),
            crs="EPSG:4326"
        ).to_crs("EPSG:3310")
        
        # Indexed lookups
        self.node_lookup = self.nodes_df.set_index('node_id').to_dict('index')
        self.addresses = self.nodes_gdf[self.nodes_gdf['node_type'] == 'Address']
        self.places = self.nodes_gdf[self.nodes_gdf['node_type'] == 'Place']
        self.buildings = self.nodes_gdf[self.nodes_gdf['node_type'] == 'Building']
        self.parcels = self.nodes_gdf[self.nodes_gdf['node_type'] == 'Parcel']
        
        self.address_strings = self.addresses.apply(
            lambda r: f"{r.get('number', '')} {r.get('street', '')}".strip().lower(), axis=1
        ).unique().tolist()
        self.building_names = self.buildings['name'].dropna().str.lower().unique().tolist()
        self.place_names = self.places['name'].dropna().str.lower().unique().tolist()

    def find_node(self, query):
        """Find any node by name, address, or ID using fuzzy matching."""
        q = query.lower().strip()
        
        # 1. Check if it's a known address
        close_addr = difflib.get_close_matches(q, self.address_strings, n=1, cutoff=0.8)
        if close_addr:
            match_str = close_addr[0]
            return self.nodes_df[self.nodes_df.apply(lambda r: f"{r.get('number', '')} {r.get('street', '')}".lower() == match_str, axis=1)].iloc[0].to_dict()

        # 2. Check if it's a building name
        close_bldg = difflib.get_close_matches(q, self.building_names, n=1, cutoff=0.8)
        if close_bldg:
            return self.nodes_df[self.nodes_df['name'].str.lower() == close_bldg[0]].iloc[0].to_dict()

        # 3. Check if it's a place name
        close_place = difflib.get_close_matches(q, self.place_names, n=1, cutoff=0.8)
        if close_place:
            return self.nodes_df[self.nodes_df['name'].str.lower() == close_place[0]].iloc[0].to_dict()
            
        return None

    def get_related(self, node_id, rel_type=None, direction='both'):
        """Get related nodes and their data."""
        results = []
        
        if direction in ['out', 'both']:
            for dst_id, rtype, props in self.adj_out.get(node_id, []):
                if rel_type is None or rtype == rel_type:
                    results.append({'id': dst_id, 'rel': rtype, 'dir': 'out', 'props': props, 'node': self.node_lookup.get(dst_id)})
                    
        if direction in ['in', 'both']:
            for src_id, rtype, props in self.adj_in.get(node_id, []):
                if rel_type is None or rtype == rel_type:
                    results.append({'id': src_id, 'rel': rtype, 'dir': 'in', 'props': props, 'node': self.node_lookup.get(src_id)})
                    
        return results

    def traverse(self, start_node_id, path_types):
        """Multi-hop traversal. path_types is a list of (rel_type, direction) tuples."""
        current_ids = [start_node_id]
        for rel_type, direction in path_types:
            next_ids = []
            for cid in current_ids:
                related = self.get_related(cid, rel_type, direction)
                next_ids.extend([r['id'] for r in related])
            current_ids = list(set(next_ids))
        return [self.node_lookup[nid] for nid in current_ids if nid in self.node_lookup]

    def format_node(self, node):
        if node is None: return "Unknown Entity"
        ntype = node.get('node_type', 'Entity')
        if ntype == 'Parcel':
            return f"Parcel {node.get('apn', 'Unknown')} ({node.get('land_use', 'Property')})"
        name = node.get('name') or f"{node.get('number', '')} {node.get('street', '')}".strip() or ntype
        return f"{name} ({ntype})"

    def query(self, text):
        text = text.lower().strip()
        
        # 1. Relation-based queries: "What businesses are in [Building/Address]?"
        rel_match = re.search(r"(businesses|places|what|is)\s+(?:.*?)\s*(?:in|inside|at)\s+(.*)", text)
        if rel_match and any(x in text for x in ["businesses", "places", "inside", "what is in", "what is at"]):
            target = rel_match.group(2).strip()
            node = self.find_node(target)
            if node:
                # Try multiple paths for Places
                # Path A: Entity <- IN_BUILDING - Place
                # Path B: Entity <- HAS_ADDRESS - Place
                # Path C: Entity -> HAS_ADDRESS -> Address <- HAS_ADDRESS - Place
                places = []
                # Direct relationships
                for r in self.get_related(node['node_id'], direction='in'):
                    if r['node'] and r['node']['node_type'] == 'Place':
                        places.append(r['node'])
                
                if not places:
                    # Multi-hop via Address
                    places = self.traverse(node['node_id'], [('HAS_ADDRESS', 'out'), ('HAS_ADDRESS', 'in')])
                    places = [p for p in places if p['node_type'] == 'Place']
                
                # Remove duplicates
                seen = {p['node_id'] for p in places}
                places_unique = []
                for p in places:
                    if p['node_id'] in seen:
                        places_unique.append(p)
                        seen.remove(p['node_id'])
                
                if places_unique:
                    resp = f"I found {len(places_unique)} places associated with {self.format_node(node)}:\n"
                    for p in places_unique[:20]: resp += f"- {p.get('name')} ({p.get('category')})\n"
                    return resp
                return f"I couldn't find any recorded places inside or at {self.format_node(node)}."
            if target:
                return f"I couldn't locate the building or address '{target}'."

        # 2. Info Lookup: "Tell me about [Entity]"
        info_match = re.search(r"(tell me about|info for|what is at|what is)\s+(.*)", text)
        if info_match:
            target = info_match.group(2).strip()
            node = self.find_node(target)
            if node:
                resp = f"Information for {self.format_node(node)}:\n"
                for k in ['class', 'category', 'subtype', 'height', 'num_floors']:
                    val = node.get(k)
                    if val and str(val).lower() != 'nan': resp += f"- {k.capitalize()}: {val}\n"
                
                parcel = self.traverse(node['node_id'], [('ON_PARCEL', 'out')])
                if parcel: resp += f"- Parcel: {parcel[0].get('apn')} ({parcel[0].get('land_use')})\n"

                neighbors = self.get_related(node['node_id'])
                if neighbors:
                    resp += "\nConnected Entities:\n"
                    seen_labels = set()
                    for n in neighbors:
                        label = self.format_node(n['node'])
                        if label not in seen_labels:
                            direction_label = 'to' if n['dir'] == 'out' else 'from'
                            resp += f"- {n['rel']} {direction_label} {label}\n"
                            seen_labels.add(label)
                            if len(seen_labels) >= 5: break
                return resp
            return f"I couldn't find any information for '{target}'."

        # 3. Parcel/Ownership queries
        if any(x in text for x in ["parcel", "belongs to", "on the same parcel"]):
            # Extract target more carefully
            target = text
            for x in ["parcel is", "belongs to", "on the same parcel as", "what is the parcel for"]:
                if x in text:
                    target = text.split(x)[-1].strip()
                    break
            
            node = self.find_node(target)
            if node:
                parcels = self.traverse(node['node_id'], [('ON_PARCEL', 'out')])
                if parcels:
                    p = parcels[0]
                    resp = f"{self.format_node(node)} is located on Parcel {p.get('apn')}.\n"
                    resp += f"Land Use: {p.get('land_use')}\n"
                    
                    if "same parcel" in text:
                        others = self.traverse(p['node_id'], [('ON_PARCEL', 'in')])
                        others = [o for o in others if o['node_id'] != node['node_id']]
                        if others:
                            resp += f"\nOther entities on this same parcel:\n"
                            for o in others[:10]: resp += f"- {self.format_node(o)}\n"
                    return resp
                return f"I don't have parcel information for {self.format_node(node)}."
            return f"I couldn't find '{target}' to look up parcel info."

        # 3. Address queries
        if any(x in text for x in ["address of", "where is"]):
            target = text.replace("address of", "").replace("where is", "").strip()
            node = self.find_node(target)
            if node:
                if node['node_type'] == 'Address':
                    return f"That is an address: {node.get('number')} {node.get('street')}."
                
                addrs = self.traverse(node['node_id'], [('HAS_ADDRESS', 'out')])
                if not addrs and node['node_type'] == 'Place':
                    addrs = self.traverse(node['node_id'], [('IN_BUILDING', 'out'), ('HAS_ADDRESS', 'out')])
                
                if addrs:
                    a = addrs[0]
                    return f"The address for {self.format_node(node)} is {a.get('number')} {a.get('street')}."
                return f"I couldn't find a specific address record for {self.format_node(node)}."
            return f"I couldn't locate '{target}'."

        # 4. Proximity queries
        prox_match = re.search(r"(how many|find|list)\s+(.*?)\s+(near|from|around|within\s+(\d+)\s*m\s+of)\s+(.*)", text)
        if prox_match:
            category, radius, target = prox_match.group(2).strip(), int(prox_match.group(4)) if prox_match.group(4) else 500, prox_match.group(5).strip()
            # Clean up category (e.g. "coffee shops" -> "coffee")
            cat_query = category.replace("shops", "").replace("shop", "").replace("stores", "").replace("store", "").strip()
            
            origin_node = self.find_node(target)
            if origin_node:
                origin_geom = self.nodes_gdf[self.nodes_gdf['node_id'] == origin_node['node_id']].iloc[0].geometry
                buffer = origin_geom.buffer(radius)
                nearby = self.places[self.places.geometry.within(buffer)]
                
                if cat_query and cat_query not in ['places', 'things', 'entities']:
                    nearby = nearby[nearby['category'].str.lower().str.contains(cat_query, na=False) | 
                                    nearby['name'].str.lower().str.contains(cat_query, na=False)]
                
                resp = f"I found {len(nearby)} '{category}' within {radius}m of {self.format_node(origin_node)}.\n"
                if not nearby.empty:
                    nearby = nearby.copy()
                    nearby['dist'] = nearby.geometry.distance(origin_geom)
                    for _, r in nearby.sort_values('dist').head(10).iterrows():
                        resp += f"- {r.get('name')} ({r.get('category')}): {r['dist']:.0f}m away\n"
                return resp
            return f"I couldn't find the origin location '{target}'."

        # 5. Default Info Lookup
        node = self.find_node(text)
        if node:
            resp = f"Information for {self.format_node(node)}:\n"
            for k in ['class', 'category', 'subtype', 'height', 'num_floors']:
                if node.get(k): resp += f"- {k.capitalize()}: {node[k]}\n"
            
            parcel = self.traverse(node['node_id'], [('ON_PARCEL', 'out')])
            if parcel: resp += f"- Parcel: {parcel[0].get('apn')}\n"

            neighbors = self.get_related(node['node_id'])
            if neighbors:
                resp += "\nConnected Entities:\n"
                seen = set()
                for n in neighbors:
                    label = self.format_node(n['node'])
                    if label not in seen:
                        direction_label = 'to' if n['dir'] == 'out' else 'from'
                        resp += f"- {n['rel']} {direction_label} {label}\n"
                        seen.add(label)
                        if len(seen) >= 5: break
            return resp

        return "I can answer questions about Sierra Madre's entities and their connections. Try:\n- 'What businesses are in [Building]?'\n- 'What parcel is [Address] on?'\n- 'Find coffee shops near [Place]'\n- 'Tell me about [Address]'"

def main():
    try:
        chatbot = PropertyGraphChatbot()
        print("\n=== Sierra Madre Spatial Graph Chatbot ===")
        print("Ready for queries. Type 'exit' to quit.")
        
        while True:
            query = input("\nQuery: ")
            if query.lower() in ['exit', 'quit', 'bye']: break
            if not query.strip(): continue
            print("-" * 40)
            print(chatbot.query(query))
            print("-" * 40)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
