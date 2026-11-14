"""
03 - Submit the Long Beach polygon (created in the dashboard) to /v1/heatmap and save the result.
Input:    long_beach_polygon.geojson, 2022-03-16, filter_type=3 (single day), 100 m, tcm.
          Area 23.85 km2, no scaling.
Observed: 2,397 tiles; min/max/mean 17.5688 / 18.1553 / 17.9113 C
          (dashboard panel: 17.57 / 18.16 / 17.91). Finished in about 30 s.
Output:   result_lb.json (compared with the dashboard layer offline in 05)
Cost:     4,220 credits.
"""
import os, time, json, requests

BASE = "https://api.fortyguard.com/v1"
H = {"api-key": os.environ["FORTYGUARD_API_KEY"], "Content-Type": "application/json"}

payload = {
    "polygon_aoi": json.load(open("long_beach_polygon.geojson", encoding="utf-8")),
    "date_time": {"start_date": "2022-03-16", "filter_type": 3},  # single day
    "granularity": 100,
    "analytic_type": "tcm",
}

t0 = time.time()
r = requests.post(f"{BASE}/heatmap", headers=H, json=payload, timeout=60)
print("Submit:", r.status_code, r.text[:300])
r.raise_for_status()
aid = r.json()["data"]["activity_id"]

delay, data = 5, None
for _ in range(120):
    s = requests.get(f"{BASE}/status/{aid}", headers=H, timeout=60)
    if s.status_code in (404, 429):
        delay = min(delay * 2, 30)
    elif s.ok:
        d = s.json()["data"]
        status = d["status"].lower()
        print(f"[{time.time()-t0:.0f}s] {status}")
        if status in ("completed", "succeeded"):
            data = d
            json.dump(s.json(), open("result_lb.json", "w"))
            break
        if status in ("failed", "error"):
            raise SystemExit(f"FAILED: {s.text[:300]}")
    time.sleep(delay)

if data is None:
    raise SystemExit("timeout")

print("API stats:", data["result"]["stats_data"]["temperature_stats"])
print("Dashboard stats panel: min 17.57 max 18.16 mean 17.91 sd 0.21")
print("tiles:", len(data["result"]["map_data"]["features"]))