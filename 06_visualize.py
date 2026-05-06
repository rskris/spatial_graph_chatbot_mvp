"""
Generate the Sierra Madre Property Graph interactive map.
"""

from __future__ import annotations

import json
import math
import warnings
from pathlib import Path

import pandas as pd
from shapely import wkt as swkt
from shapely.geometry import mapping

import config

warnings.filterwarnings("ignore")

# Sierra Madre Viewport
VIS_BBOX = config.BBOX
MAP_CENTER = [(config.BBOX["ymin"] + config.BBOX["ymax"]) / 2, (config.BBOX["xmin"] + config.BBOX["xmax"]) / 2]
MAP_ZOOM   = 15

OUT_DIR  = Path("data/vis")
OUT_HTML = Path("data/property_graph_map.html")

LAND_USE_COLORS = {
    "SINGLE FAMILY": "#4A90D9",
    "MULTI-FAMILY":  "#2D6FAB",
    "COMMERCIAL":    "#F5A623",
    "INDUSTRIAL":    "#D0021B",
    "AGRICULTURAL":  "#7ED321",
    "VACANT":        "#9B9B9B",
    "GOVERNMENTAL":  "#8B5CF6",
    "RECREATIONAL":  "#50C878",
}

BUILDING_CLASS_COLORS = {
    "residential":   "#5B9BD5",
    "commercial":    "#F59E0B",
    "industrial":    "#EF4444",
    "agricultural":  "#84CC16",
    "civic":         "#8B5CF6",
    "education":     "#6366F1",
    "religious":     "#A78BFA",
    "transportation":"#F97316",
    "outbuilding":   "#9CA3AF",
}

PLACE_CAT_COLORS = {
    "eat_and_drink":          "#EF4444",
    "retail":                 "#F97316",
    "accommodation":          "#F59E0B",
    "health_and_medical":     "#10B981",
    "arts_and_entertainment": "#8B5CF6",
    "education":              "#6366F1",
    "government":             "#3B82F6",
    "services":               "#06B6D4",
    "travel":                 "#84CC16",
}

def _color_for(val: str, palette: dict, default="#94A3B8") -> str:
    v = (val or "").lower()
    for k, c in palette.items():
        if k.lower() in v:
            return c
    return default

def _safe(v):
    if v is None: return None
    if isinstance(v, float) and math.isnan(v): return None
    return v

def _in_bbox(lon, lat, b) -> bool:
    try: return b["xmin"] <= float(lon) <= b["xmax"] and b["ymin"] <= float(lat) <= b["ymax"]
    except Exception: return False

def _simplify(geom, tol=0.00005):
    s = geom.simplify(tol, preserve_topology=True)
    d = mapping(s)
    def rnd(c):
        if isinstance(c[0], (int, float)): return [round(c[0], 5), round(c[1], 5)]
        return [rnd(x) for x in c]
    return {**d, "coordinates": rnd(d["coordinates"])}

def build_parcels(df: pd.DataFrame) -> dict:
    rows = df[df["node_type"] == "Parcel"]
    rows = rows[rows.apply(lambda r: _in_bbox(r.get("lon"), r.get("lat"), VIS_BBOX), axis=1)]
    feats = []
    for _, r in rows.iterrows():
        wkt = r.get("geometry_wkt")
        if not wkt: continue
        try: geom = swkt.loads(wkt)
        except Exception: continue
        lu = _safe(r.get("land_use")) or ""
        feats.append({
            "type": "Feature",
            "geometry": _simplify(geom),
            "properties": {
                "id": r["node_id"], "type": "Parcel", "apn": _safe(r.get("apn")),
                "address": _safe(r.get("situs_address")), "land_use": lu,
                "year_built": _safe(r.get("year_built")), "sq_ft": _safe(r.get("sq_footage")),
                "bedrooms": _safe(r.get("bedrooms")), "bathrooms": _safe(r.get("bathrooms")),
                "land_val": _safe(r.get("land_value")), "color": _color_for(lu, LAND_USE_COLORS),
                "label": f"Parcel {r.get('apn','')}", "cx": _safe(r.get("lon")), "cy": _safe(r.get("lat")),
            },
        })
    return {"type": "FeatureCollection", "features": feats}

def build_buildings(df: pd.DataFrame) -> dict:
    rows = df[df["node_type"] == "Building"]
    rows = rows[rows.apply(lambda r: _in_bbox(r.get("lon"), r.get("lat"), VIS_BBOX), axis=1)]
    feats = []
    for _, r in rows.iterrows():
        wkt = r.get("geometry_wkt")
        if not wkt: continue
        try: geom = swkt.loads(wkt)
        except Exception: continue
        cls = _safe(r.get("class")) or ""
        feats.append({
            "type": "Feature",
            "geometry": _simplify(geom, tol=0.00002),
            "properties": {
                "id": r["node_id"], "type": "Building", "name": _safe(r.get("name")),
                "class": cls, "subtype": _safe(r.get("subtype")), "height": _safe(r.get("height")),
                "floors": _safe(r.get("num_floors")), "color": _color_for(cls, BUILDING_CLASS_COLORS),
                "label": _safe(r.get("name")) or f"Building ({cls})", "cx": _safe(r.get("lon")), "cy": _safe(r.get("lat")),
            },
        })
    return {"type": "FeatureCollection", "features": feats}

def build_addresses(df: pd.DataFrame) -> dict:
    rows = df[df["node_type"] == "Address"]
    rows = rows[rows.apply(lambda r: _in_bbox(r.get("lon"), r.get("lat"), VIS_BBOX), axis=1)]
    feats = []
    for _, r in rows.iterrows():
        lon, lat = _safe(r.get("lon")), _safe(r.get("lat"))
        if lon is None or lat is None: continue
        num = _safe(r.get("number")) or ""; street = _safe(r.get("street")) or ""
        feats.append({
            "type": "Feature", "geometry": {"type": "Point", "coordinates": [round(lon,5), round(lat,5)]},
            "properties": {"id": r["node_id"], "type": "Address", "number": num, "street": street,
                           "label": f"{num} {street}".strip() or "Address", "cx": lon, "cy": lat},
        })
    return {"type": "FeatureCollection", "features": feats}

def build_places(df: pd.DataFrame) -> dict:
    rows = df[df["node_type"] == "Place"]
    rows = rows[rows.apply(lambda r: _in_bbox(r.get("lon"), r.get("lat"), VIS_BBOX), axis=1)]
    feats = []
    for _, r in rows.iterrows():
        lon, lat = _safe(r.get("lon")), _safe(r.get("lat"))
        if lon is None or lat is None: continue
        cat = _safe(r.get("category")) or ""
        feats.append({
            "type": "Feature", "geometry": {"type": "Point", "coordinates": [round(lon,5), round(lat,5)]},
            "properties": {"id": r["node_id"], "type": "Place", "name": _safe(r.get("name")),
                           "category": cat, "color": _color_for(cat, PLACE_CAT_COLORS),
                           "label": _safe(r.get("name")) or f"Place ({cat})", "cx": lon, "cy": lat},
        })
    return {"type": "FeatureCollection", "features": feats}

def build_divisions(df: pd.DataFrame) -> dict:
    rows = df[df["node_type"] == "Division"]
    feats = []
    for _, r in rows.iterrows():
        wkt = r.get("geometry_wkt")
        if not wkt: continue
        try: geom = swkt.loads(wkt)
        except Exception: continue
        feats.append({
            "type": "Feature", "geometry": _simplify(geom, tol=0.0001),
            "properties": {"id": r["node_id"], "type": "Division", "name": _safe(r.get("name")),
                           "subtype": _safe(r.get("subtype")), "label": _safe(r.get("name")) or "Division",
                           "cx": _safe(r.get("lon")), "cy": _safe(r.get("lat"))},
        })
    return {"type": "FeatureCollection", "features": feats}

def build_graph(edges_df: pd.DataFrame, vis_ids: set, nodes_df: pd.DataFrame) -> dict:
    type_lookup = nodes_df.set_index("node_id")["node_type"].to_dict()
    mask = edges_df["src_id"].isin(vis_ids) | edges_df["dst_id"].isin(vis_ids)
    rel_edges = edges_df[mask]

    p_members = {}; node_parcel = {}; bldg_addr = {}; addr_bldg = {}

    for _, row in rel_edges.iterrows():
        src, dst, rel = row["src_id"], row["dst_id"], row["rel_type"]
        if rel == "ON_PARCEL":
            src_type = type_lookup.get(src, "")
            pm = p_members.setdefault(dst, {"b": [], "a": [], "pl": []})
            if src_type == "Building": pm["b"].append(src)
            elif src_type == "Address": pm["a"].append(src)
            elif src_type == "Place": pm["pl"].append(src)
            node_parcel.setdefault(src, []).append(dst)
        elif rel == "HAS_ADDRESS":
            bldg_addr.setdefault(src, []).append(dst)
            addr_bldg.setdefault(dst, []).append(src)

    member_ids = set()
    for pm in p_members.values(): member_ids.update(pm["b"], pm["a"], pm["pl"])
    all_ids = vis_ids | member_ids

    idx = {}
    sub = nodes_df[nodes_df["node_id"].isin(all_ids)]
    for _, r in sub.iterrows():
        nid = r["node_id"]; ntype = r.get("node_type", "")
        if ntype == "Parcel": color = _color_for(r.get("land_use"), LAND_USE_COLORS); label = f"Parcel {r.get('apn', '')}"
        elif ntype == "Building": color = _color_for(r.get("class"), BUILDING_CLASS_COLORS); label = r.get("name") or f"Building"
        elif ntype == "Place": color = _color_for(r.get("category"), PLACE_CAT_COLORS); label = r.get("name") or f"Place"
        elif ntype == "Address": color = "#34d399"; label = f"{r.get('number','')} {r.get('street','')}".strip()
        else: color = "#94a3b8"; label = nid[:24]
        idx[nid] = {"id": nid, "type": ntype, "label": label, "cx": _safe(r.get("lon")), "cy": _safe(r.get("lat")), "color": color}

    return {"idx": idx, "p_members": p_members, "node_parcel": node_parcel, "bldg_addr": bldg_addr, "addr_bldg": addr_bldg}

# ---------------------------------------------------------------------------
# HTML template
# ---------------------------------------------------------------------------

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Sierra Madre Property Graph</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css"/>
<link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css"/>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
     display:flex;height:100vh;overflow:hidden;background:#0f172a}

#loader{position:fixed;inset:0;background:#0f172a;z-index:9999;
        display:flex;flex-direction:column;align-items:center;justify-content:center;gap:18px}
#loader h2{color:#f1f5f9;font-size:17px;font-weight:600}
#prog-bar{width:300px;height:3px;background:#1e293b;border-radius:2px;overflow:hidden}
#prog-fill{height:100%;width:0%;background:linear-gradient(90deg,#6366f1,#a855f7);transition:width .3s;border-radius:2px}
#prog-lbl{color:#475569;font-size:11px}

#sidebar{width:340px;min-width:260px;background:#1e293b;color:#e2e8f0;
         display:flex;flex-direction:column;border-right:1px solid #334155;overflow:hidden}
#hdr{padding:13px 16px 9px;background:#0f172a;border-bottom:1px solid #334155;flex-shrink:0}
#hdr h1{font-size:13px;font-weight:700;color:#f1f5f9;letter-spacing:.3px}
#hdr p{font-size:10px;color:#475569;margin-top:2px}

#layers{padding:9px 14px;background:#111827;border-bottom:1px solid #334155;
        display:flex;flex-wrap:wrap;gap:5px;flex-shrink:0}
.ltog{display:flex;align-items:center;gap:4px;font-size:10px;color:#64748b;cursor:pointer;
      padding:3px 7px;border-radius:4px;border:1px solid #1e293b;user-select:none;transition:all .15s}
.ltog:hover{background:#1e293b}.ltog.on{color:#e2e8f0;border-color:#374151}
.ldot{width:8px;height:8px;border-radius:50%;flex-shrink:0}

#stats{padding:5px 14px;background:#0f172a;border-bottom:1px solid #1e293b;
       font-size:10px;color:#334155;display:flex;gap:10px;flex-shrink:0;flex-wrap:wrap}
.si{display:flex;align-items:center;gap:3px}
.sdot{width:5px;height:5px;border-radius:50%}

#panel{flex:1;overflow-y:auto}
#empty{display:flex;flex-direction:column;align-items:center;justify-content:center;
       height:100%;color:#1e293b;font-size:12px;text-align:center;padding:32px;gap:12px}
#empty svg{opacity:.2}
#empty span{color:#334155;line-height:1.5}

.pcard{padding:14px 16px 12px;border-bottom:1px solid #0f172a}
.badge{display:inline-flex;align-items:center;gap:5px;font-size:9px;font-weight:700;
       text-transform:uppercase;letter-spacing:1px;padding:2px 7px;border-radius:99px;margin-bottom:8px}
.badge.Parcel  {background:#4f46e515;color:#818cf8;border:1px solid #4f46e540}
.badge.Building{background:#d9770615;color:#fb923c;border:1px solid #d9770640}
.badge.Address {background:#05966915;color:#34d399;border:1px solid #05966940}
.badge.Place   {background:#7c3aed15;color:#c084fc;border:1px solid #7c3aed40}
.badge.Division{background:#be123c15;color:#fb7185;border:1px solid #be123c40}
.sel-name{font-size:15px;font-weight:700;color:#f1f5f9;line-height:1.3;margin-bottom:3px}
.sel-sub{font-size:11px;color:#64748b;margin-bottom:12px}

.pr-title{font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:1px;
          color:#334155;margin-bottom:8px;display:flex;align-items:center;gap:6px}
.pr-title::after{content:'';flex:1;height:1px;background:#1e293b}
.pr-row{display:flex;align-items:flex-start;gap:10px;margin-bottom:10px}
.pr-icon{width:30px;height:30px;border-radius:6px;display:flex;align-items:center;
         justify-content:center;flex-shrink:0;font-size:13px}
.pr-count-block{flex:1;min-width:0}
.pr-count{font-size:18px;font-weight:800;line-height:1;color:#f1f5f9}
.pr-type{font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:.6px;margin-bottom:3px}
.pr-items{display:flex;flex-direction:column;gap:1px}
.pr-item{font-size:11px;color:#94a3b8;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
         cursor:pointer;padding:1px 4px;border-radius:3px;transition:background .1s}
.pr-item:hover{background:#0f172a;color:#e2e8f0}
.pr-more{font-size:10px;color:#334155;padding:1px 4px}

.attr-title{font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:1px;
            color:#334155;margin:12px 0 6px;display:flex;align-items:center;gap:6px}
.attr-title::after{content:'';flex:1;height:1px;background:#1e293b}
.atbl{width:100%;border-collapse:collapse}
.atbl td{padding:3px 0;font-size:11px;vertical-align:top}
.atbl td:first-child{color:#475569;width:42%;padding-right:6px}
.atbl td:last-child{color:#cbd5e1;font-weight:500}

#legend{padding:9px 14px;border-top:1px solid #0f172a;flex-shrink:0}
#legend h4{font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:.8px;
           color:#1e293b;margin-bottom:5px}
.lrow{display:flex;align-items:center;gap:5px;margin-bottom:2px;font-size:10px;color:#475569}
.lsw{width:11px;height:11px;border-radius:2px;flex-shrink:0}

#map{flex:1}
.leaflet-container{background:#0f172a}
.pg-tip{background:#1e293b!important;border:1px solid #334155!important;
        color:#f1f5f9!important;font-size:11px!important;padding:5px 9px!important;
        border-radius:5px!important;box-shadow:0 4px 12px rgba(0,0,0,.5)!important}
.pg-tip::before{display:none!important}
::-webkit-scrollbar{width:4px}
::-webkit-scrollbar-track{background:#0f172a}
::-webkit-scrollbar-thumb{background:#334155;border-radius:2px}
</style>
</head>
<body>

<div id="loader">
  <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="1.5">
    <circle cx="12" cy="12" r="3"/>
    <circle cx="4"  cy="6"  r="2"/><circle cx="20" cy="6"  r="2"/>
    <circle cx="4"  cy="18" r="2"/><circle cx="20" cy="18" r="2"/>
    <line x1="6" y1="6"  x2="10" y2="11"/><line x1="18" y1="6"  x2="14" y2="11"/>
    <line x1="6" y1="18" x2="10" y2="13"/><line x1="18" y1="18" x2="14" y2="13"/>
  </svg>
  <h2>Sierra Madre Property Graph</h2>
  <div id="prog-bar"><div id="prog-fill"></div></div>
  <p id="prog-lbl">Initializing</p>
</div>

<div id="sidebar">
  <div id="hdr">
    <h1>Sierra Madre Property Graph</h1>
    <p>Overture Maps + LA County Assessor &mdash; click any feature</p>
  </div>
  <div id="layers">
    <div class="ltog on" onclick="toggleLayer('parcels',this)"><div class="ldot" style="background:#818cf8"></div>Parcels</div>
    <div class="ltog on" onclick="toggleLayer('buildings',this)"><div class="ldot" style="background:#fb923c"></div>Buildings</div>
    <div class="ltog on" onclick="toggleLayer('addresses',this)"><div class="ldot" style="background:#34d399"></div>Addresses</div>
    <div class="ltog on" onclick="toggleLayer('places',this)"><div class="ldot" style="background:#c084fc"></div>Places</div>
    <div class="ltog on" onclick="toggleLayer('divisions',this)"><div class="ldot" style="background:#fb7185"></div>Divisions</div>
  </div>
  <div id="stats">
    <span class="si"><span class="sdot" style="background:#818cf8"></span><b id="s-p">-</b>&nbsp;parcels</span>
    <span class="si"><span class="sdot" style="background:#fb923c"></span><b id="s-b">-</b>&nbsp;buildings</span>
    <span class="si"><span class="sdot" style="background:#34d399"></span><b id="s-a">-</b>&nbsp;addresses</span>
    <span class="si"><span class="sdot" style="background:#c084fc"></span><b id="s-pl">-</b>&nbsp;places</span>
  </div>
  <div id="panel">
    <div id="empty">
      <svg width="60" height="60" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
        <rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/>
        <rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>
        <line x1="6.5" y1="10" x2="6.5" y2="14"/><line x1="17.5" y1="10" x2="17.5" y2="14"/>
        <line x1="10" y1="6.5" x2="14" y2="6.5"/><line x1="10" y1="17.5" x2="14" y2="17.5"/>
      </svg>
      <span>Click a parcel, building, address,<br/>or place to see its full property record</span>
    </div>
  </div>
  <div id="legend">
    <h4>Land Use</h4>
    <div class="lrow"><div class="lsw" style="background:#4A90D9"></div>Single Family Residential</div>
    <div class="lrow"><div class="lsw" style="background:#2D6FAB"></div>Multi-Family Residential</div>
    <div class="lrow"><div class="lsw" style="background:#F5A623"></div>Commercial</div>
    <div class="lrow"><div class="lsw" style="background:#D0021B"></div>Industrial</div>
    <div class="lrow"><div class="lsw" style="background:#7ED321"></div>Agricultural</div>
    <div class="lrow"><div class="lsw" style="background:#8B5CF6"></div>Governmental</div>
    <div class="lrow"><div class="lsw" style="background:#9B9B9B"></div>Vacant</div>
  </div>
</div>

<div id="map"></div>

<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>
<script>
const LAYERS={}, LAYER_ON={parcels:true,buildings:true,addresses:true,places:true,divisions:true};
let IDX={}, selectedId=null;
const nodeLayerMap={}, nodeLatLng={};
let hlLayers=[], bboxRect=null;

const map=L.map('map',{center:MAP_CENTER_PLACEHOLDER,zoom:MAP_ZOOM_PLACEHOLDER,preferCanvas:true});
L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
  {attribution:'OpenStreetMap/CartoDB',subdomains:'abcd',maxZoom:21}).addTo(map);
const renderer=L.canvas({padding:0.5});

function setProgress(p,l){
  document.getElementById('prog-fill').style.width=p+'%';
  document.getElementById('prog-lbl').textContent=l;
}

let P_MEMBERS={}, NODE_PARCEL={}, BLDG_ADDR={}, ADDR_BLDG={};

function getRecord(nodeId){
  const rec={parcels:new Set(),buildings:new Set(),addresses:new Set(),places:new Set()};
  const self=IDX[nodeId]; if(!self) return rec;

  const parcelSeeds=new Set();
  if(self.type==='Parcel'){
    parcelSeeds.add(nodeId);
  } else {
    (NODE_PARCEL[nodeId]||[]).forEach(pid=>parcelSeeds.add(pid));
    if(self.type==='Building'){
      (BLDG_ADDR[nodeId]||[]).forEach(aid=>{
        (NODE_PARCEL[aid]||[]).forEach(pid=>parcelSeeds.add(pid));
      });
    }
    if(self.type==='Address'){
      (ADDR_BLDG[nodeId]||[]).forEach(bid=>{
        (NODE_PARCEL[bid]||[]).forEach(pid=>parcelSeeds.add(pid));
      });
    }
  }

  parcelSeeds.forEach(pid=>{
    rec.parcels.add(pid);
    const pm=P_MEMBERS[pid]||{b:[],a:[],pl:[]};
    pm.b.forEach(id=>rec.buildings.add(id));
    pm.a.forEach(id=>rec.addresses.add(id));
    pm.pl.forEach(id=>rec.places.add(id));
  });

  Array.from(rec.buildings).forEach(bid=>{
    (BLDG_ADDR[bid]||[]).forEach(aid=>rec.addresses.add(aid));
  });

  Array.from(rec.addresses).forEach(aid=>{
    (ADDR_BLDG[aid]||[]).forEach(bid=>{
      rec.buildings.add(bid);
      (NODE_PARCEL[bid]||[]).forEach(pid=>{
        rec.parcels.add(pid);
        const pm=P_MEMBERS[pid]||{b:[],a:[],pl:[]};
        pm.b.forEach(id=>rec.buildings.add(id));
        pm.a.forEach(id=>rec.addresses.add(id));
        pm.pl.forEach(id=>rec.places.add(id));
      });
    });
  });

  if(self.type==='Building') rec.buildings.add(nodeId);
  else if(self.type==='Address') rec.addresses.add(nodeId);
  else if(self.type==='Place') rec.places.add(nodeId);

  return rec;
}

function clearHL(){
  if(bboxRect){map.removeLayer(bboxRect);bboxRect=null;}
  hlLayers.forEach(l=>map.removeLayer(l)); hlLayers=[];
  Object.values(nodeLayerMap).forEach(l=>{
    if(l._origStyle){l.setStyle(l._origStyle);delete l._origStyle;}
  });
}

function applyHL(rec,selId){
  clearHL();
  const allIds=[...rec.parcels,...rec.buildings,...rec.addresses,...rec.places];
  const bounds=L.latLngBounds([]);
  allIds.forEach(id=>{
    const ll=nodeLatLng[id]; if(ll) bounds.extend(ll);
    const l=nodeLayerMap[id]; if(l&&l.getBounds) bounds.extend(l.getBounds());
  });

  rec.parcels.forEach(id=>{
    const l=nodeLayerMap[id]; if(!l) return;
    const sel=id===selId;
    if(!l._origStyle) l._origStyle={fillColor:l.options.fillColor,fillOpacity:l.options.fillOpacity,color:l.options.color,weight:l.options.weight};
    l.setStyle({fillColor:'#a78bfa',fillOpacity:sel?0.55:0.3,color:'#7c3aed',weight:sel?2.5:1.5});
    l.bringToFront();
  });
  rec.buildings.forEach(id=>{
    const l=nodeLayerMap[id]; if(!l) return;
    const sel=id===selId;
    if(!l._origStyle) l._origStyle={fillColor:l.options.fillColor,fillOpacity:l.options.fillOpacity,color:l.options.color,weight:l.options.weight};
    l.setStyle({fillColor:'#f97316',fillOpacity:sel?0.92:0.75,color:'#fff',weight:sel?2:1.2});
    l.bringToFront();
  });
  rec.addresses.forEach(id=>{
    const ll=nodeLatLng[id]; if(!ll) return;
    const ring=L.circleMarker(ll,{renderer,radius:id===selId?9:6,fillColor:'#34d399',
      color:'#fff',weight:id===selId?2:1,fillOpacity:0.95,interactive:false}).addTo(map);
    hlLayers.push(ring);
  });
  rec.places.forEach(id=>{
    const ll=nodeLatLng[id]; if(!ll) return;
    const n=IDX[id];
    const ring=L.circleMarker(ll,{renderer,radius:id===selId?10:7,fillColor:n?n.color:'#c084fc',
      color:'#fff',weight:2,fillOpacity:0.9,interactive:false}).addTo(map);
    hlLayers.push(ring);
  });

  if(bounds.isValid()&&allIds.length>1){
    bboxRect=L.rectangle(bounds,{color:'#f97316',weight:2,dashArray:'8 5',fill:false,interactive:false}).addTo(map);
  }
}

function fmt(v){if(v==null) return '&mdash;'; if(typeof v==='number') return v.toLocaleString(); return String(v);}
function fmtUSD(v){return v?'$'+Number(v).toLocaleString():'&mdash;';}

function recRow(color,icon,count,label,ids,maxShow){
  if(count===0) return '';
  const items=ids.slice(0,maxShow).map(id=>{
    const n=IDX[id]; if(!n) return '';
    const lbl=escHtml(n.label||n.id.slice(0,28));
    return '<div class="pr-item" onclick="focusNode(\''+n.id+'\')" title="'+lbl+'">'+lbl+'</div>';
  }).join('');
  const more=ids.length>maxShow?'<div class="pr-more">+' +(ids.length-maxShow)+' more</div>':'';
  return '<div class="pr-row">'
    +'<div class="pr-icon" style="background:'+color+'18;border:1px solid '+color+'35">'+icon+'</div>'
    +'<div class="pr-count-block">'
    +'<div style="display:flex;align-items:baseline;gap:6px">'
    +'<div class="pr-count" style="color:'+color+'">'+count+'</div>'
    +'<div class="pr-type">'+label+'</div></div>'
    +'<div class="pr-items">'+items+more+'</div>'
    +'</div></div>';
}

function escHtml(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}

function attrTbl(p){
  const MAP={apn:'APN',address:'Situs Address',situs_address:'Situs Address',land_use:'Land Use',year_built:'Year Built',
    sq_ft:'Sq Ft',bedrooms:'Beds',bathrooms:'Baths',land_val:'Land Value',net_av:'Net Assessed Value',
    acreage:'Acreage',name:'Name',class:'Class',subtype:'Subtype',height:'Height (m)',floors:'Floors',
    number:'House #',street:'Street',postcode:'Postcode',category:'Category',status:'Op. Status',phones:'Phone'};
  let rows='';
  for(const [k,lbl] of Object.entries(MAP)){
    let v=p[k]; if(v==null||v===''||v==='None') continue;
    let d=(k==='land_val'||k==='net_av')?fmtUSD(v):fmt(v);
    rows+='<tr><td>'+lbl+'</td><td>'+d+'</td></tr>';
  }
  return rows?'<table class="atbl">'+rows+'</table>':'';
}

function showPanel(props){
  selectedId=props.id;
  const rec=getRecord(selectedId);
  applyHL(rec,selectedId);

  const ntype=props.type, panel=document.getElementById('panel');
  const sub={Address:props.street||'',Building:props.class||'',
             Parcel:props.land_use||'',Place:props.category||'',Division:''}[ntype]||'';

  const parcelIds  =Array.from(rec.parcels);
  const buildingIds=Array.from(rec.buildings);
  const addrIds    =Array.from(rec.addresses);
  const placeIds   =Array.from(rec.places);

  const PFIELDS=['year_built','sq_ft','bedrooms','bathrooms','land_val','net_av','acreage','land_use'];
  let attrCount=0;
  parcelIds.forEach(pid=>{
    const pn=IDX[pid]||{};
    attrCount+=PFIELDS.filter(f=>pn[f]&&pn[f]!==''&&pn[f]!=='None').length;
  });
  if(ntype==='Parcel') attrCount=PFIELDS.filter(f=>props[f]&&props[f]!==''&&props[f]!=='None').length;

  panel.innerHTML=
    '<div class="pcard">'
    +'<div class="badge '+ntype+'">'+ntype+'</div>'
    +'<div class="sel-name">'+escHtml(props.label||props.name||props.apn||ntype)+'</div>'
    +(sub?'<div class="sel-sub">'+escHtml(sub)+'</div>':'')
    +'<div class="pr-title">Property Record</div>'
    +recRow('#a78bfa','&#9636;',parcelIds.length,parcelIds.length===1?'Parcel':'Parcels',parcelIds,4)
    +recRow('#fb923c','&#11035;',buildingIds.length,buildingIds.length===1?'Building':'Buildings',buildingIds,4)
    +recRow('#34d399','&#9679;',addrIds.length,addrIds.length===1?'Address':'Addresses',addrIds,6)
    +(placeIds.length?recRow('#c084fc','&#9733;',placeIds.length,placeIds.length===1?'Business / Place':'Businesses / Places',placeIds,5):'')
    +(attrCount?recRow('#64748b','&#8801;',attrCount,'Property Attribute Fields',[],0):'')
    +'<div class="attr-title">Attributes</div>'
    +attrTbl(props)
    +'</div>';
}

function focusNode(id){
  const n=IDX[id]; if(!n) return;
  if(n.cx&&n.cy) map.panTo([n.cy,n.cx]);
  const l=nodeLayerMap[id];
  if(l&&l.feature) showPanel(l.feature.properties);
  else showPanel(Object.assign({id:n.id,label:n.label,type:n.type,color:n.color},n));
}

function toggleLayer(name,btn){
  LAYER_ON[name]=!LAYER_ON[name];
  btn.classList.toggle('on',LAYER_ON[name]);
  const lg=LAYERS[name];
  if(lg){LAYER_ON[name]?map.addLayer(lg):map.removeLayer(lg);}
}

function addParcels(data){
  document.getElementById('s-p').textContent=data.features.length.toLocaleString();
  const lg=L.geoJSON(data,{renderer,
    style:f=>({fillColor:f.properties.color,fillOpacity:0.25,color:f.properties.color,weight:0.7,opacity:0.55}),
    onEachFeature(f,layer){
      const p=f.properties;
      nodeLayerMap[p.id]=layer; layer.feature=f;
      const c=layer.getBounds?layer.getBounds().getCenter():null;
      if(c) nodeLatLng[p.id]=[c.lat,c.lng];
      if(IDX[p.id]) Object.assign(IDX[p.id],p);
      layer.on('click',()=>showPanel(p));
      layer.bindTooltip('<b>'+escHtml(p.label)+'</b><br>'+(p.land_use||'')+'<br>'+(p.address||''),{className:'pg-tip',sticky:true});
      layer.on('mouseover',()=>{if(!layer._origStyle) layer.setStyle({fillOpacity:0.45,weight:1.4});});
      layer.on('mouseout', ()=>{if(!layer._origStyle) lg.resetStyle(layer);});
    }}).addTo(map);
  LAYERS.parcels=lg;
}

function addBuildings(data){
  document.getElementById('s-b').textContent=data.features.length.toLocaleString();
  const lg=L.geoJSON(data,{renderer,
    style:f=>({fillColor:f.properties.color,fillOpacity:0.65,color:'#fff',weight:0.4,opacity:0.3}),
    onEachFeature(f,layer){
      const p=f.properties;
      nodeLayerMap[p.id]=layer; layer.feature=f;
      const c=layer.getBounds?layer.getBounds().getCenter():null;
      if(c) nodeLatLng[p.id]=[c.lat,c.lng];
      if(IDX[p.id]) Object.assign(IDX[p.id],p);
      layer.on('click',()=>showPanel(p));
      layer.bindTooltip('<b>'+escHtml(p.label)+'</b><br>Class: '+(p.class||'-')+' &middot; Floors: '+(p.floors||'-'),{className:'pg-tip',sticky:true});
      layer.on('mouseover',()=>{if(!layer._origStyle) layer.setStyle({fillOpacity:0.88,weight:1.2,color:'#fff'});});
      layer.on('mouseout', ()=>{if(!layer._origStyle) lg.resetStyle(layer);});
    }}).addTo(map);
  LAYERS.buildings=lg;
}

function addAddresses(data){
  document.getElementById('s-a').textContent=data.features.length.toLocaleString();
  const cluster=L.markerClusterGroup({maxClusterRadius:28,disableClusteringAtZoom:18,
    iconCreateFunction:c=>L.divIcon({
      html:'<div style="background:#059669;color:#fff;border-radius:50%;width:22px;height:22px;display:flex;align-items:center;justify-content:center;font-size:9px;font-weight:700;border:1.5px solid #34d399">'+c.getChildCount()+'</div>',
      className:'',iconSize:[22,22]})});
  data.features.forEach(f=>{
    const p=f.properties,[lon,lat]=f.geometry.coordinates;
    nodeLatLng[p.id]=[lat,lon];
    if(IDX[p.id]) Object.assign(IDX[p.id],p);
    const m=L.circleMarker([lat,lon],{renderer,radius:3,fillColor:'#34d399',color:'#059669',weight:1,fillOpacity:0.85});
    nodeLayerMap[p.id]=m; m.feature=f;
    m.on('click',()=>showPanel(p));
    m.bindTooltip('<b>'+escHtml(p.label)+'</b>',{className:'pg-tip'});
    cluster.addLayer(m);
  });
  cluster.addTo(map); LAYERS.addresses=cluster;
}

function addPlaces(data){
  document.getElementById('s-pl').textContent=data.features.length.toLocaleString();
  const cluster=L.markerClusterGroup({maxClusterRadius:36,disableClusteringAtZoom:18,
    iconCreateFunction:c=>L.divIcon({
      html:'<div style="background:#7c3aed;color:#fff;border-radius:50%;width:22px;height:22px;display:flex;align-items:center;justify-content:center;font-size:9px;font-weight:700;border:1.5px solid #c084fc">'+c.getChildCount()+'</div>',
      className:'',iconSize:[22,22]})});
  data.features.forEach(f=>{
    const p=f.properties,[lon,lat]=f.geometry.coordinates;
    nodeLatLng[p.id]=[lat,lon];
    if(IDX[p.id]) Object.assign(IDX[p.id],p);
    const icon=L.divIcon({html:'<div style="background:'+p.color+';width:9px;height:9px;border-radius:50%;border:1.5px solid rgba(255,255,255,.5)"></div>',className:'',iconSize:[9,9],iconAnchor:[4,4]});
    const m=L.marker([lat,lon],{icon});
    nodeLayerMap[p.id]=m; m.feature=f;
    m.on('click',()=>showPanel(p));
    m.bindTooltip('<b>'+escHtml(p.label)+'</b><br>'+(p.category||''),{className:'pg-tip'});
    cluster.addLayer(m);
  });
  cluster.addTo(map); LAYERS.places=cluster;
}

function addDivisions(data){
  const lg=L.geoJSON(data,{renderer,
    style:{fillColor:'transparent',color:'#4f46e5',weight:2,opacity:0.35,dashArray:'6 4'},
    onEachFeature(f,layer){
      const p=f.properties;
      const c=layer.getBounds?layer.getBounds().getCenter():null;
      if(c) nodeLatLng[p.id]=[c.lat,c.lng];
      layer.bindTooltip('<b>'+escHtml(p.label)+'</b> &middot; '+(p.subtype||''),{className:'pg-tip',sticky:true});
    }}).addTo(map);
  LAYERS.divisions=lg;
}

async function init(){
  try{
    setProgress(5,'Loading data files');
    const base='vis/';
    const [parcels,buildings,addresses,places,divisions,graph]=await Promise.all([
      fetch(base+'parcels.json').then(r=>{if(!r.ok)throw new Error(r.status+' parcels');return r.json();}),
      fetch(base+'buildings.json').then(r=>{if(!r.ok)throw new Error(r.status);return r.json();}),
      fetch(base+'addresses.json').then(r=>{if(!r.ok)throw new Error(r.status);return r.json();}),
      fetch(base+'places.json').then(r=>{if(!r.ok)throw new Error(r.status);return r.json();}),
      fetch(base+'divisions.json').then(r=>{if(!r.ok)throw new Error(r.status);return r.json();}),
      fetch(base+'graph.json').then(r=>{if(!r.ok)throw new Error(r.status);return r.json();}),
    ]);
    IDX=graph.idx;
    P_MEMBERS=graph.p_members||{};
    NODE_PARCEL=graph.node_parcel||{};
    BLDG_ADDR=graph.bldg_addr||{};
    ADDR_BLDG=graph.addr_bldg||{};
    setProgress(65,'Rendering parcels');    addParcels(parcels);
    setProgress(74,'Rendering buildings');  addBuildings(buildings);
    setProgress(82,'Rendering addresses');  addAddresses(addresses);
    setProgress(90,'Rendering places');     addPlaces(places);
    setProgress(96,'Rendering divisions');  addDivisions(divisions);
    setProgress(100,'Ready');
    setTimeout(()=>document.getElementById('loader').style.display='none',300);
  }catch(e){
    document.getElementById('prog-lbl').textContent='Error: '+e.message;
    document.getElementById('prog-fill').style.background='#ef4444';
    console.error(e);
  }
}
init();
</script>
</body>
</html>
"""

def main():
    nodes_path = Path("data/nodes.parquet")
    edges_path = Path("data/edges.parquet")

    if not nodes_path.exists():
        print("ERROR: Run 02_build_graph.py and 05_integrate_parcels.py first.")
        return

    print("=== Property Graph Visualizer ===\n")
    print(f"Viewport: {VIS_BBOX}\n")

    print("Loading nodes & edges…")
    nodes_df = pd.read_parquet(nodes_path)
    edges_df = pd.read_parquet(edges_path) if edges_path.exists() else pd.DataFrame()
    print(f"  {len(nodes_df):,} nodes · {len(edges_df):,} edges")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\nBuilding layers…")
    layers = {
        "parcels":   build_parcels(nodes_df),
        "buildings": build_buildings(nodes_df),
        "addresses": build_addresses(nodes_df),
        "places":    build_places(nodes_df),
        "divisions": build_divisions(nodes_df),
    }
    for name, fc in layers.items():
        n = len(fc["features"])
        path = OUT_DIR / f"{name}.json"
        path.write_text(json.dumps(fc, separators=(",",":")), encoding="utf-8")
        sz = path.stat().st_size / 1024
        print(f"  {name:12s}: {n:6,} features  →  {sz:7.0f} KB")

    vis_ids: set[str] = set()
    for fc in layers.values():
        for feat in fc["features"]:
            vis_ids.add(feat["properties"]["id"])
    print(f"\n  Visible nodes: {len(vis_ids):,}")

    print("Building graph lookup tables…")
    graph = build_graph(edges_df, vis_ids, nodes_df)
    graph_path = OUT_DIR / "graph.json"
    graph_path.write_text(json.dumps(graph, separators=(",",":")), encoding="utf-8")
    graph_sz = graph_path.stat().st_size / 1024
    print(f"  graph.json:    {len(graph['idx']):,} nodes in idx, "
          f"{len(graph['p_members']):,} parcels, "
          f"{len(graph['node_parcel']):,} node→parcel entries  →  {graph_sz:.0f} KB")

    html = HTML \
        .replace("MAP_CENTER_PLACEHOLDER", json.dumps(MAP_CENTER)) \
        .replace("MAP_ZOOM_PLACEHOLDER",   str(MAP_ZOOM))

    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"\nDone. Visualization generated in {OUT_HTML}")

if __name__ == "__main__":
    main()
