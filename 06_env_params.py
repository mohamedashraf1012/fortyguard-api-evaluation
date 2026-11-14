"""
06 - First call to /v1/env_params (Environmental Parameters).
Input:    Long Beach centre (33.8166, -118.1083), temperature=17.9 C (required by the API),
          2022-03-16, single day, all parameters (no "analysis" field).
Observed: completed in 5 s; timezone America/Los_Angeles (-07:00); 24 hourly values per parameter;
          9 of 15 parameters (all AQI values, methane, CO2) are null for all 24 hours,
          with no reason given in the response.
Output:   result_env.json
Cost:     2,900 credits.
"""
import os, time, json, requests

BASE = "https://api.fortyguard.com/v1"
H = {"api-key": os.environ["FORTYGUARD_API_KEY"], "Content-Type": "application/json"}

payload = {
    "latitude": 33.8166,
    "longitude": -118.1083,
    "temperature": 17.9,   # Celsius, per the docs
    "date_time": {"start_date": "2022-03-16", "filter_type": 3},
    # no "analysis" field: Premium returns all parameters
}

t0 = time.time()
r = requests.post(f"{BASE}/env_params", headers=H, json=payload, timeout=60)
print("Submit:", r.status_code, r.text[:300])
r.raise_for_status()
aid = r.json()["data"]["activity_id"]

delay, body = 5, None
for _ in range(120):
    s = requests.get(f"{BASE}/status/{aid}", headers=H, timeout=60)
    if s.status_code in (404, 429):
        delay = min(delay * 2, 30)
    elif s.ok:
        b = s.json()
        st = b["data"]["status"].lower()
        print(f"[{time.time()-t0:.0f}s] {st}")
        if st in ("completed", "succeeded"):
            body = b
            json.dump(b, open("result_env.json", "w"), indent=2)
            break
        if st in ("failed", "error"):
            raise SystemExit(f"FAILED: {s.text[:300]}")
    time.sleep(delay)

res = body["data"]["result"]
print("result keys:", list(res.keys()))
print("metadata:", json.dumps(res.get("metadata"))[:400])
print("locations:", json.dumps(res.get("locations"))[:300])

def walk(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            walk(v, f"{path}/{k}")
    elif isinstance(o, list) and o and all(isinstance(x, (int, float)) or x is None for x in o):
        nums = [x for x in o if isinstance(x, (int, float)) and x != -999]
        extra = f" min={min(nums)} max={max(nums)}" if nums else ""
        print(f"{path}: n={len(o)} null={o.count(None)} minus999={o.count(-999)}{extra}")
    elif isinstance(o, list):
        for i, v in enumerate(o[:3]):
            walk(v, f"{path}[{i}]")

walk(res)