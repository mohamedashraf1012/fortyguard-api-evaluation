"""
12 - Read the live MCP server's full tool descriptions and resources, then read stored heatmap statistics.
Questions: (1) What do the tool descriptions and the 4 resources (coverage, units, data_quality, entitlements) say that the
              docs pages do not? (2) What statistics does the backend store for the dashboard's own heatmaps
              (Long Beach and the California demo), compared with the dashboard panel and the REST result?
Method:    MCP tools/list, resources/read, tools/call heatmap_read and credit_balance (read-only).
Output:    mcp_dump.txt (full descriptions and resources; kept local), heatmap_read results printed.
Cost:      none expected; each response includes trace.cost_credits, which this script prints.
"""
import os, json, requests

URL = "https://tos-mcp.app.fortyguard.com/mcp"
H = {"Authorization": f"Bearer {os.environ['FORTYGUARD_API_KEY']}",
     "Content-Type": "application/json",
     "Accept": "application/json, text/event-stream"}
_id = [0]

def parse(resp):
    resp.encoding = "utf-8"   # requests assumes Latin-1 for text/event-stream
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
    r = requests.post(URL, headers=H, json=body, timeout=120)
    return r, parse(r)

r, _ = rpc("initialize", {"protocolVersion": "2025-03-26", "capabilities": {},
                          "clientInfo": {"name": "eval-check", "version": "0.1"}})
if r.headers.get("Mcp-Session-Id"):
    H["Mcp-Session-Id"] = r.headers["Mcp-Session-Id"]
rpc("notifications/initialized", notify=True)

tools = rpc("tools/list")[1]["result"]["tools"]
resources = rpc("resources/list")[1]["result"]["resources"]

with open("mcp_dump.txt", "w", encoding="utf-8") as f:
    f.write("# TOOLS (full descriptions)\n")
    for t in tools:
        f.write(f"\n## {t['name']}\n{t.get('description', '')}\n")
        for name, p in t.get("inputSchema", {}).get("properties", {}).items():
            enum = f" enum={p['enum']}" if "enum" in p else ""
            f.write(f"  - {name} ({p.get('type', '?')}){enum}: {(p.get('description') or '')[:400]}\n")
    f.write("\n# RESOURCES\n")
    for res in resources:
        contents = rpc("resources/read", {"uri": res["uri"]})[1]["result"]["contents"]
        f.write(f"\n## {res['name']} ({res['uri']})\n" + "\n".join(c.get("text", "") for c in contents) + "\n")
print("wrote mcp_dump.txt")

def call(name, args):
    r, data = rpc("tools/call", {"name": name, "arguments": args})
    print(f"\n=== {name} {args} | HTTP {r.status_code}")
    for c in ((data or {}).get("result", {}).get("content", [])):
        try:
            j = json.loads(c["text"])
            print("value:", json.dumps(j.get("result", {}).get("value"), indent=1)[:1800])
            print("warnings:", j.get("result", {}).get("warnings"), "| cost_credits:", j.get("trace", {}).get("cost_credits"))
        except Exception:
            print(c.get("text", "")[:800])

call("heatmap_read", {"heatmap_id": "f5b3844f-0df6-4fbf-9ab2-9f5754ed5d3b"})   # dashboard: California demo
call("heatmap_read", {"heatmap_id": "f3029bd3-b4a7-4b41-ab74-c6e56227cf0b"})   # dashboard: Long Beach
call("heatmap_read", {"activity_id": "daf472d3-f282-4552-9640-8140f9102851"})   # REST: Long Beach
call("heatmap_read", {"activity_id": "8ec13f14-2d6b-48f1-8107-25039d83bcdf"})   # MCP (Cursor): Long Beach
call("credit_balance", {})