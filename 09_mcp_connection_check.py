"""
09 - Test the FortyGuard MCP endpoint directly with Python (no MCP client involved).
Question: Does the MCP server accept my API key, independent of Cursor's configuration?
Method:   send MCP `initialize` and `tools/list` over Streamable HTTP, once with my key and once
          with a deliberately invalid key, and compare the responses.
Cost:     none (no tool is executed).
"""
import os, json, requests

URL = "https://tos-mcp.app.fortyguard.com/mcp"
KEY = os.environ.get("FORTYGUARD_API_KEY", "")
print(f"key present: {bool(KEY)} | length: {len(KEY)} | has surrounding whitespace: {KEY != KEY.strip()}")

def parse(resp):
    """The reply is either plain JSON or a server-sent-events stream ('data: {...}')."""
    if "text/event-stream" in resp.headers.get("content-type", ""):
        for line in resp.text.splitlines():
            if line.startswith("data:"):
                return json.loads(line[5:].strip())
        return None
    return resp.json() if resp.text.strip() else None

def check(key, label):
    print(f"\n=== {label} ===")
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json",
               "Accept": "application/json, text/event-stream"}
    init = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-03-26", "capabilities": {},
                       "clientInfo": {"name": "eval-check", "version": "0.1"}}}
    r = requests.post(URL, headers=headers, json=init, timeout=30)
    print("initialize ->", r.status_code, r.headers.get("content-type"))
    if r.status_code != 200:
        print("body:", r.text[:400])
        return
    session = r.headers.get("Mcp-Session-Id")
    if session:
        headers["Mcp-Session-Id"] = session
    requests.post(URL, headers=headers, json={"jsonrpc": "2.0", "method": "notifications/initialized"}, timeout=30)
    t = requests.post(URL, headers=headers, json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, timeout=30)
    print("tools/list ->", t.status_code)
    data = parse(t)
    tools = (data or {}).get("result", {}).get("tools", [])
    print(f"tools: {len(tools)}")
    for tool in tools:
        print(" -", tool["name"])

check(KEY, "my API key")
check("invalid-key-for-comparison", "deliberately invalid key")