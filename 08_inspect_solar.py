"""
08 - Inspect the solar_irradiance block of result_env.json (offline).
Observed: one clear-sky daytime average (GHI 516.42, DNI 665.21, DHI 106.26 W/m2) plus a text
          description, not the time-aligned arrays the docs describe.
"""
import json

res = json.load(open("result_env.json"))["data"]["result"]
loc, ts = res["locations"][0], res["metadata"]["timestamps"]
sol = loc["solar_irradiance"]
print("type:", type(sol).__name__)
print("raw sample:", json.dumps(sol)[:500])

def series(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from series(v, f"{path}/{k}")
    elif isinstance(o, list) and len(o) == 24 and all(isinstance(x, (int, float)) or x is None for x in o):
        yield path, o

for path, v in series(sol):
    nums = [x for x in v if x is not None]
    print(f"\n{path}: null={v.count(None)} min={min(nums) if nums else None} max={max(nums) if nums else None}")
    if nums:
        print("  peak at:", ts[v.index(max(nums))][11:16], "| 00-05h:", v[0:6], "| 22-23h:", v[22:24])
        print("  night (0-4h) all zero:", all((x or 0) == 0 for x in v[0:5]))
print("\ncloud_cover_octas:", loc["parameters"]["cloud_cover_octas"])