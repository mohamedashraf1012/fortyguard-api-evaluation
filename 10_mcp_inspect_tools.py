"""
10 - Inspect the FortyGuard MCP server directly with Python (no MCP client involved).
Question: What does the live server expose, compared with the documented catalog of 9 tools?
Method:   MCP `tools/list` (name, description, inputs), `resources/list`, then `tools/call credit_balance`.
Cost:     none expected (read-only). The `monitoring` tool is listed but NOT called.
"""
import os, json, requests

URL = "https://tos-mcp.app.fortyguard.com/mcp"
H = {"Authorization": f"Bearer {os.environ['FORTYGUARD_API_KEY']}",
     "Content-Type": "application/json",
     "Accept": "application/json, text/event-stream"}

def parse(resp):
    if "text/event-stream" in resp.headers.get("content-type", ""):
        for line in resp.text.splitlines():
            if line.startswith("data:"):
                return json.loads(line[5:].strip())
        return None
    return resp.json() if resp.text.strip() else None

def rpc(method, params=None, id_=None):
    body = {"jsonrpc": "2.0", "method": method}
    if params is not None:
        body["params"] = params
    if id_ is not None:
        body["id"] = id_
    r = requests.post(URL, headers=H, json=body, timeout=60)
    return r, parse(r)

r, _ = rpc("initialize", {"protocolVersion": "2025-03-26", "capabilities": {},
                          "clientInfo": {"name": "eval-check", "version": "0.1"}}, 1)
if r.headers.get("Mcp-Session-Id"):
    H["Mcp-Session-Id"] = r.headers["Mcp-Session-Id"]
rpc("notifications/initialized")

_, data = rpc("tools/list", id_=2)
tools = data["result"]["tools"]
print(f"{len(tools)} tools\n")
for t in tools:
    schema = t.get("inputSchema", {})
    print(f"## {t['name']}")
    print("  description:", (t.get("description") or "")[:300].replace("\n", " "))
    print("  inputs:", list(schema.get("properties", {}).keys()), "| required:", schema.get("required", []))

print("\n=== resources ===")
_, res = rpc("resources/list", id_=4)
print(json.dumps((res or {}).get("result", res), indent=2)[:1500])

print("\n=== credit_balance ===")
r, data = rpc("tools/call", {"name": "credit_balance", "arguments": {}}, 3)
print("HTTP", r.status_code)
print(json.dumps(data, indent=2)[:1500])