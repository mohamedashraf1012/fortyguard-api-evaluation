"""
01 - Run the official Quickstart example exactly as documented.
Question: Does the example from the docs work with my key?
Request:  POST /v1/heatmap, Lower Manhattan, 2024-07-15 14:00 (filter_type=1), 100 m.
Expected: A heatmap (activity_id, then status completed).
Observed: HTTP 400 OUT_OF_COVERAGE on field polygon_aoi. The docs do not list coverage.
Cost:     None expected (request rejected; credits are charged only on completion).
"""
import os
import time
import json
import requests

API_KEY = os.environ["FORTYGUARD_API_KEY"]
BASE = "https://api.fortyguard.com/v1"
HEADERS = {"api-key": API_KEY, "Content-Type": "application/json"}

payload = {
    "polygon_aoi": {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [-74.0170, 40.7050],
                    [-74.0030, 40.7050],
                    [-74.0030, 40.7180],
                    [-74.0170, 40.7180],
                    [-74.0170, 40.7050],
                ]],
            },
        }],
    },
    "date_time": {"start_date": "2024-07-15", "start_time": "14:00", "filter_type": 1},
    "granularity": 100,
}

# 1) Submit the request
start = time.time()
r = requests.post(f"{BASE}/heatmap", headers=HEADERS, json=payload, timeout=30)
print("Submit status code:", r.status_code)
print("Submit response:", r.text[:500])
r.raise_for_status()
activity_id = r.json()["data"]["activity_id"]
print("activity_id:", activity_id)

# 2) Poll the status every 5 seconds
for _ in range(120):
    s = requests.get(f"{BASE}/status/{activity_id}", headers=HEADERS, timeout=30)
    print(f"[{time.time()-start:.0f}s] status code:", s.status_code)
    if s.ok:
        data = s.json()["data"]
        status = data["status"].lower()
        print("status:", status)
        if status in ("completed", "succeeded"):
            with open("result.json", "w") as f:
                json.dump(s.json(), f, indent=2)
            print("Done! Saved to result.json")
            break
        if status in ("failed", "error"):
            print("Task failed:", s.text[:500])
            break
    time.sleep(5)