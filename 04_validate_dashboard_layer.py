"""
04 - Validate the heatmap layer exported from the dashboard (offline).
Input:    heatmap_layer.geojson (Long Beach, 2022-03-16). Not committed to the repo.
Observed: 57,528 features = 2,397 tiles x 24 hourly timestamps; values are Fahrenheit (temperature_f).
          Hourly values range 12.6-24.9 C. (The dashboard panel's min/max/mean are statistics of
          the per-tile DAILY means, so they are not comparable with this hourly SD of 3.57 C.)
"""
import json, statistics as st
from collections import Counter

LAYER = "heatmap_layer.geojson"   # exported from the dashboard
feats = json.load(open(LAYER, encoding="utf-8"))["features"]

ids = [f["properties"]["tile_id"] for f in feats]
print("features:", len(feats), "| unique tile_id:", len(set(ids)), "| range:", min(ids), max(ids))
print("timestamps:", Counter(f["properties"]["timestamp"] for f in feats).most_common(5))

c = [(f["properties"]["temperature_f"] - 32) / 1.8 for f in feats]
q1, q2, q3 = st.quantiles(c, n=4)
print(f"C: min={min(c):.4f} max={max(c):.4f} mean={st.mean(c):.4f} sd={st.pstdev(c):.4f}")
print(f"Q1/med/Q3: {q1:.4f} / {q2:.4f} / {q3:.4f}")
print("dashboard: min 17.57 max 18.16 mean 17.91 sd 0.21 | Q1 17.86 med 17.89 Q3 18.02")

lo, hi, n = min(c), max(c), 8
w = (hi - lo) / n
b = Counter(min(int((x - lo) / w), n - 1) for x in c)
for i in range(n):
    print(f"{lo + i*w:.2f}-{lo + (i+1)*w:.2f}: {b[i]}")