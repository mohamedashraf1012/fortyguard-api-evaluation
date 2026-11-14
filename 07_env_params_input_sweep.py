"""
07 - Does the `temperature` input change the /v1/env_params output?
Same location and date as 06, with temperature = 10, 17.9 (re-uses result_env.json) and 35.
Observed: only heat_index_celsius depends on the input; apparent temperature, wet-bulb, humidity
          and cloud cover are identical in all three runs. At 35 C the heat index reaches 70.8 C
          while the apparent temperature in the same response stays 12-20 C, with no warning.
Output:   result_env_10.json, result_env_35.json
Cost:     2 x 2,900 credits.
"""
import os, time, json, requests

BASE = "https://api.fortyguard.com/v1"
H = {"api-key": os.environ["FORTYGUARD_API_KEY"], "Content-Type": "application/json"}

def run(temp):
    payload = {"latitude": 33.8166, "longitude": -118.1083, "temperature": temp,
               "date_time": {"start_date": "2022-03-16", "filter_type": 3}}
    r = requests.post(f"{BASE}/env_params", headers=H, json=payload, timeout=60)
    print(f"temp={temp}: submit {r.status_code}")
    r.raise_for_status()
    aid, delay = r.json()["data"]["activity_id"], 5
    for _ in range(120):
        s = requests.get(f"{BASE}/status/{aid}", headers=H, timeout=60)
        if s.status_code in (404, 429):
            delay = min(delay * 2, 30)
        elif s.ok:
            b = s.json()
            st = b["data"]["status"].lower()
            if st in ("completed", "succeeded"):
                json.dump(b, open(f"result_env_{temp}.json", "w"), indent=2)
                return b
            if st in ("failed", "error"):
                raise SystemExit(f"FAILED: {s.text[:300]}")
        time.sleep(delay)
    raise SystemExit("timeout")

runs = {17.9: json.load(open("result_env.json"))}
for t in (10, 35):
    runs[t] = run(t)

for t in sorted(runs):
    loc = runs[t]["data"]["result"]["locations"][0]
    p = loc["parameters"]
    print(f"\n=== temperature input = {t} ===")
    print("location keys:", list(loc.keys()))
    for k in ("heat_index_celsius", "apparent_temperature_celsius", "wet_bulb_temperature_celsius",
              "relative_humidity_percent", "cloud_cover_octas"):
        v = [x for x in p[k] if x is not None]
        print(f"  {k}: min={min(v)} max={max(v)}")
    hi = p["heat_index_celsius"]
    print(f"  heat_index == input temp for all hours: {all(x == t for x in hi)}")