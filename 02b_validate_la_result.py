"""
02b - Offline checks on result_la.json (no API call, no credits).
Checks: nulls, tile_id uniqueness, min <= avg <= max per tile, tile size in metres.
Observed: no nulls, unique tile_id, no violations, tiles about 101 m x 101 m.
"""
import json, math

body = json.load(open("result_la.json"))
res = body["data"]["result"]
feats = res["map_data"]["features"]

for p in ["average_temperature", "min_temperature", "max_temperature"]:
    vals = [f["properties"].get(p) for f in feats]
    nn = [v for v in vals if v is not None]
    print(f"{p}: nulls={len(vals)-len(nn)} min={min(nn):.4f} max={max(nn):.4f} "
          f"mean={sum(nn)/len(nn):.4f} distinct={len(set(nn))}")

ids = [f["properties"]["tile_id"] for f in feats]
print("tile_id unique:", len(set(ids)) == len(ids), "| range:", min(ids), max(ids))

def ok(p):
    a, lo, hi = p.get("average_temperature"), p.get("min_temperature"), p.get("max_temperature")
    return None in (a, lo, hi) or lo <= a <= hi
bad = [f["properties"]["tile_id"] for f in feats if not ok(f["properties"])]
print("tiles violating min <= avg <= max:", len(bad))

ring = feats[0]["geometry"]["coordinates"][0]
lons = [p[0] for p in ring]; lats = [p[1] for p in ring]
lat0 = sum(lats) / len(lats)
w = (max(lons) - min(lons)) * 111320 * math.cos(math.radians(lat0))
h = (max(lats) - min(lats)) * 110574
print(f"first tile size ~ {w:.0f} m x {h:.0f} m")