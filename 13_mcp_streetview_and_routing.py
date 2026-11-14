"""
13 - Run the remaining MCP tests with a direct Python client (my Cursor usage limit ran out).
Modes:  streetview         vertical_angle=90, horizontal_angle=0 (compare with the 0/0 and 0/90 runs done in Cursor)
        streetview-repeat  vertical_angle=0, horizontal_angle=0 again (run-to-run noise of the segmentation)
        routing            temperature_routing for about 20 km, then polls temperature_routing_read and times it
Cost:   8,600 credits (each streetview run), 3,500 credits (routing). Each mode asks for confirmation first.
Output: prints a summary; full results are saved to result_<mode>.json (kept local).
"""
import os, sys, json, time, requests

URL = "https://tos-mcp.app.fortyguard.com/mcp"
H = {"Authorization": f"Bearer {os.environ['FORTYGUARD_API_KEY']}",
     "Content-Type": "application/json",
     "Accept": "application/json, text/event-stream"}
_id = [0]

def parse(resp):
    resp.encoding = "utf-8"
    if "text/event-stream" in resp.headers.get("content-type", ""):
        for line in resp.text.splitlines():
            if line.startswith("data:"):
                return json.loads(line[5:].strip())
        return None
    return resp.json() if resp.text.strip() else None

def rpc(method, params=None, notify=False):
    body = {"jsonrpc": "2.0", "method": method}
    if params is not None:
        body["params"] = params
    if not notify:
        _id[0] += 1
        body["id"] = _id[0]
    r = requests.post(URL, headers=H, json=body, timeout=180)
    return r, parse(r)

def call_tool(name, args):
    r, data = rpc("tools/call", {"name": name, "arguments": args})
    res = (data or {}).get("result", {})
    text = (res.get("content") or [{}])[0].get("text", "")
    try:
        return json.loads(text), bool(res.get("isError"))
    except Exception:
        return {"raw": text or json.dumps(data)[:600]}, True

def find_key(obj, name):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.lower() == name:
                return v
            f = find_key(v, name)
            if f is not None:
                return f
    elif isinstance(obj, list):
        for v in obj:
            f = find_key(v, name)
            if f is not None:
                return f
    return None

def value_of(j):
    return (j.get("result") or {}).get("value")

def confirm(cost):
    if input(f"This costs {cost:,} credits. Type YES to continue: ").strip() != "YES":
        sys.exit("cancelled")

def balance():
    j, _ = call_tool("credit_balance", {})
    print("credits now:", (value_of(j) or {}).get("available_credits"))

mode = sys.argv[1] if len(sys.argv) > 1 else ""
r, _ = rpc("initialize", {"protocolVersion": "2025-03-26", "capabilities": {},
                          "clientInfo": {"name": "eval-check", "version": "0.1"}})
if r.headers.get("Mcp-Session-Id"):
    H["Mcp-Session-Id"] = r.headers["Mcp-Session-Id"]
rpc("notifications/initialized", notify=True)

if mode in ("streetview", "streetview-repeat"):
    v_angle = 90 if mode == "streetview" else 0
    args = {"latitude": 33.8166, "longitude": -118.1083, "vertical_angle": v_angle,
            "horizontal_angle": 0, "back_view": False}
    print("streetview args:", args)
    confirm(8600)
    j, err = call_tool("streetview", args)
    json.dump(j, open(f"result_{mode}.json", "w"), indent=2)
    print("error:", err, "| cost_credits:", (j.get("trace") or {}).get("cost_credits"))
    v = value_of(j)
    print("warnings:", (j.get("result") or {}).get("warnings"))
    segs = find_key(v, "segments")
    if isinstance(segs, dict):
        for k, p in sorted(segs.items(), key=lambda kv: -float(kv[1]) if isinstance(kv[1], (int, float)) else 0):
            print(f"  {k}: {p}")
    else:
        print("value (truncated):", json.dumps(v)[:1200])
    print("image_date:", find_key(v, "image_date"))
    balance()

elif mode == "routing":
    tools = {t["name"]: t for t in rpc("tools/list")[1]["result"]["tools"]}
    schema = tools["temperature_routing"]["inputSchema"]
    origin_schema = schema["properties"]["origin"]
    if "$ref" in origin_schema:
        origin_schema = schema.get("$defs", {}).get(origin_schema["$ref"].split("/")[-1], {})
    print("origin schema:", json.dumps(origin_schema)[:400])
    props = origin_schema.get("properties", {})
    lat_k, lon_k = ("lat", "lon") if "lat" in props and "lon" in props else \
                   ("lat", "lng") if "lat" in props and "lng" in props else ("latitude", "longitude")
    origin = {lat_k: 33.7701, lon_k: -118.1937}
    dest = {lat_k: 33.9401, lon_k: -118.1332}
    confirm(3500)
    aid, t_submit = None, None
    for dep in ("2026-11-15T14:00:00-08:00", "2026-11-13T14:00:00-08:00"):
        print("departure_time:", dep)
        t_submit = time.time()
        j, err = call_tool("temperature_routing", {"origin": origin, "destination": dest, "departure_time": dep})
        print("submit error:", err, "| cost_credits:", (j.get("trace") or {}).get("cost_credits"))
        aid = find_key(value_of(j) or {}, "activity_id")
        if aid:
            print("activity_id:", aid)
            break
        print("not accepted:", json.dumps(j)[:500])
    if not aid:
        sys.exit("no activity accepted")
    for _ in range(120):
        j, err = call_tool("temperature_routing_read", {"activity_id": aid})
        v = value_of(j) or {}
        status = str(v.get("status", "")).lower() if isinstance(v, dict) else ""
        print(f"[{time.time() - t_submit:.0f}s] {status}")
        if status in ("completed", "succeeded"):
            break
        if status in ("failed", "error"):
            print(json.dumps(j)[:800])
            break
        time.sleep(5)
    print(f"total time from submit to {status}: {time.time() - t_submit:.0f} s")
    json.dump(j, open("result_routing.json", "w"), indent=2)
    print("value keys:", list(v.keys()) if isinstance(v, dict) else type(v))
    routes = find_key(v, "routes") or []
    print("routes:", len(routes))
    for i, rt in enumerate(routes):
        if isinstance(rt, dict):
            print(f" route {i}:", {k: x for k, x in rt.items() if not isinstance(x, (dict, list))})
            print("   keys:", list(rt.keys()))
    print("other fields:", json.dumps({k: x for k, x in v.items() if k != "routes"})[:700])
    balance()

else:
    sys.exit("usage: python 13_mcp_streetview_and_routing.py streetview | streetview-repeat | routing")