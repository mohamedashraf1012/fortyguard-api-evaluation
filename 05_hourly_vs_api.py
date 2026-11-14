"""
05 - Compare the API result (result_lb.json) with the dashboard's hourly layer, tile by tile (offline).
Method:   group the layer's 24 hourly values per tile and compare their mean/min/max with the API's
          average_temperature / min_temperature / max_temperature. Also checks the grid.
Observed: same 2,397 tiles and identical first corner of tile 0; avg max diff 0.0002 C; min exact;
          max differs by up to 0.16 C. SD of per-tile daily means = 0.1193 (API 0.1193;
          dashboard panel says 0.21).
"""
import json, statistics as st
from collections import defaultdict

LAYER = "heatmap_layer.geojson"
api_feats = json.load(open("result_lb.json"))["data"]["result"]["map_data"]["features"]
api = {f["properties"]["tile_id"]: f["properties"] for f in api_feats}
layer_feats = json.load(open(LAYER, encoding="utf-8"))["features"]

hours = defaultdict(list)
for f in layer_feats:
    p = f["properties"]
    hours[p["tile_id"]].append((p["temperature_f"] - 32) / 1.8)
print("hours per tile:", {len(v) for v in hours.values()})
print("tiles: api", len(api), "| dashboard", len(hours))

# same grid? compare the first corner of tile 0
api_t0 = next(f for f in api_feats if f["properties"]["tile_id"] == 0)
dash_t0 = next(f for f in layer_feats if f["properties"]["tile_id"] == 0)
print("tile 0 first corner  api:", api_t0["geometry"]["coordinates"][0][0])
print("tile 0 first corner dash:", dash_t0["geometry"]["coordinates"][0][0])

d_avg, d_min, d_max, means = [], [], [], []
for tid, v in hours.items():
    a, m = api[tid], sum(v) / len(v)
    means.append(m)
    d_avg.append(a["average_temperature"] - m)
    d_min.append(a["min_temperature"] - min(v))
    d_max.append(a["max_temperature"] - max(v))

for name, d in (("avg", d_avg), ("min", d_min), ("max", d_max)):
    print(f"{name}: mean diff={st.mean(d):.4f}  max|diff|={max(abs(x) for x in d):.4f}")

print(f"per-tile daily mean: min={min(means):.4f} max={max(means):.4f} "
      f"mean={st.mean(means):.4f} sd={st.pstdev(means):.4f}")
print("dashboard panel sd 0.21 | API sd 0.1193")