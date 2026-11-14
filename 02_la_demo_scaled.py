"""
02 - Reproduce the dashboard's California demo through the API.
Question: Does /v1/heatmap return the same values as the dashboard demo (LA, 2022-01-20, 100 m)?
Input:    demo_polygon.geojson (exported from the dashboard, 163 km2). It is over the API limit
          of 129.5 km2, so it is shrunk to 87% around its centre (123.6 km2).
          filter_type=3 (single day), analytic_type=tcm.
Observed: 12,363 tiles, 13.63-14.70 C (SD 0.20). The dashboard shows 13.8-38.9 C. Not explained.
Output:   result_la.json
Cost:     4,220 credits.
"""
import os, time, json, requests

BASE = "https://api.fortyguard.com/v1"
H = {"api-key": os.environ["FORTYGUARD_API_KEY"], "Content-Type": "application/json"}

with open("demo_polygon.geojson") as f:
    polygon_aoi = json.load(f)

# Shrink the polygon around its centre to fit under the 50 mi2 (129.5 km2) limit
SCALE = 0.87
ring = polygon_aoi["features"][0]["geometry"]["coordinates"][0]
c_lon = (min(p[0] for p in ring) + max(p[0] for p in ring)) / 2
c_lat = (min(p[1] for p in ring) + max(p[1] for p in ring)) / 2
polygon_aoi["features"][0]["geometry"]["coordinates"][0] = [
    [round(c_lon + (x - c_lon) * SCALE, 6), round(c_lat + (y - c_lat) * SCALE, 6)]
    for x, y in ring
]

payload = {
    "polygon_aoi": polygon_aoi,
    "date_time": {"start_date": "2022-01-20", "filter_type": 3},  # Single Day
    "granularity": 100,
    "analytic_type": "tcm",
}

def find_key(obj, name):
    """Search for a key at any nesting level (the response shape was unknown at the time)."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.lower() == name:
                return v
            found = find_key(v, name)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = find_key(v, name)
            if found is not None:
                return found
    return None

start = time.time()
r = requests.post(f"{BASE}/heatmap", headers=H, json=payload, timeout=60)
print("Submit:", r.status_code, r.text[:400])
r.raise_for_status()
activity_id = r.json()["data"]["activity_id"]
print("activity_id:", activity_id)

delay = 5
for _ in range(120):
    s = requests.get(f"{BASE}/status/{activity_id}", headers=H, timeout=30)
    print(f"[{time.time()-start:.0f}s] HTTP {s.status_code}")
    if s.status_code in (404, 429):
        delay = min(delay * 2, 30)
    elif s.ok:
        body = s.json()
        status = body["data"]["status"].lower()
        print("status:", status)
        if status in ("completed", "succeeded"):
            with open("result_la.json", "w") as f:
                json.dump(body, f, indent=2)
            print("Saved result_la.json | data keys:", list(body["data"].keys()))
            stats = find_key(body, "stats_data")
            print("stats_data:", json.dumps(stats, indent=2)[:800])
            break
        if status in ("failed", "error"):
            print("Failed:", s.text[:500])
            break
    time.sleep(delay)