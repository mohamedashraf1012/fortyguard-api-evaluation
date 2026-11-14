"""
11 - Separate date from location for the null parameters in /v1/env_params.
Question: Long Beach 2022-03-16 returned 9 null parameters (AQI, methane, CO2) while Phoenix 2025-09-20 (via MCP)
          returned values. Is it the date or the place?
Method:   same Long Beach coordinates as script 06, but date 2025-09-20 (same temperature input 17.9).
Cost:     2,900 credits.
"""
import os, time, json, requests

BASE = "https://api.fortyguard.com/v1"
H = {"api-key": os.environ["FORTYGUARD_API_KEY"], "Content-Type": "application/json"}
payload = {"latitude": 33.8166, "longitude": -118.1083, "temperature": 17.9,
           "date_time": {"start_date": "2025-09-20", "filter_type": 3}}

r = requests.post(f"{BASE}/env_params", headers=H, json=payload, timeout=60)
print("Submit:", r.status_code, r.text[:200])
r.raise_for_status()
aid, delay, body = r.json()["data"]["activity_id"], 5, None
for _ in range(120):
    s = requests.get(f"{BASE}/status/{aid}", headers=H, timeout=60)
    if s.status_code in (404, 429):
        delay = min(delay * 2, 30)
    elif s.ok:
        b = s.json()
        st = b["data"]["status"].lower()
        if st in ("completed", "succeeded"):
            body = b
            json.dump(b, open("result_env_lb_2025.json", "w"), indent=2)
            break
        if st in ("failed", "error"):
            raise SystemExit(f"FAILED: {s.text[:300]}")
    time.sleep(delay)

print("activity_id:", aid)
for k, v in body["data"]["result"]["locations"][0]["parameters"].items():
    print(f"{k}: null={v.count(None)}/{len(v)}")