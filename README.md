# FortyGuard API evaluation

An independent evaluation of FortyGuard's Temperature Dashboard, Temperature API and MCP server, prepared
for the product-evaluation step of my Data Engineering internship application. I treated the API as a new
data source: run the official example, compare its output with the dashboard, validate the data for
internal consistency, and probe edge cases. I do not have a climate background, so I focused on data
quality, schema and documentation rather than model accuracy.

**Full findings: [FINDINGS.md](FINDINGS.md)**

All numbers come from a Premium test key. Most tests use one area: Long Beach, California, on 2022-03-16
(a heatmap I created in the dashboard). I also tested the dashboard's California demo and a few
single-point calls.

## Setup (Windows PowerShell)
```powershell
pip install -r requirements.txt
$env:FORTYGUARD_API_KEY="<your key>"   # never commit this
```
REST scripts send the key in an `api-key` header; MCP scripts send `Authorization: Bearer <key>`,
which is how the docs describe each interface.

## How the API works
Each REST request returns an `activity_id`. I poll `GET /v1/status/{activity_id}` until the status is
`completed`, and the result comes back in the same response. Credits are charged on completion.

## How I tested the MCP server
I first connected Cursor (it only worked when launched from a shell that had the key set), and ran
`env_params` and `heatmap` through it. Because Cursor's usage limit ran out, I tested the rest with a direct
Python client over the same Streamable HTTP endpoint (scripts 09-13). Paid tools ask for confirmation
before running.

## Scripts
Every script starts with a docstring: question, input, observed result and credit cost (Premium plan).

| Script | What it does | Calls API? | Credits per run |
|---|---|---|---|
| `01_quickstart_official_example.py` | Runs the official Quickstart example | REST (rejected, 400) | 0 |
| `02_la_demo_scaled.py` | Reproduces the dashboard's California demo | REST | 4,220 |
| `02b_validate_la_result.py` | Checks the LA result: nulls, unique tile ids, min <= avg <= max, tile size | No | 0 |
| `03_long_beach_submit.py` | Sends the Long Beach polygon created in the dashboard | REST | 4,220 |
| `04_validate_dashboard_layer.py` | Validates the heatmap layer exported from the dashboard | No | 0 |
| `05_hourly_vs_api.py` | Compares the API result with the dashboard layer, tile by tile | No | 0 |
| `06_env_params.py` | First call to `/v1/env_params` | REST | 2,900 |
| `07_env_params_input_sweep.py` | Tests how the `temperature` input affects `/v1/env_params` | REST | 5,800 |
| `08_inspect_solar.py` | Inspects the `solar_irradiance` block | No | 0 |
| `09_mcp_connection_check.py` | Tests the MCP endpoint with my key and with an invalid key | MCP (no tool run) | 0 |
| `10_mcp_inspect_tools.py` | Lists the live MCP tools with descriptions and inputs; reads `credit_balance` | MCP (read-only) | 0 |
| `11_env_params_date_test.py` | Same place as 06 with a 2025 date, to separate date from location for the null parameters | REST | 2,900 |
| `12_mcp_descriptions_and_resources.py` | Dumps full tool descriptions and the 4 resources; reads stored heatmap statistics | MCP (read-only) | 0 |
| `13_mcp_streetview_and_routing.py` | `streetview` angle tests (including a repeat run) and `temperature_routing` | MCP | 8,600 per streetview run, 3,500 routing |
| `make_samples.py` | Creates `long_beach_api_sample.json` | No | 0 |

## Data policy
Large raw responses and the dashboard's exported heatmap layer are not committed: they are large and they
are FortyGuard's data. They stay local: `result_la.json`, `result_lb.json`, `heatmap_layer.geojson`,
`result_routing.json`, `result_streetview*.json`, and `mcp_dump.txt` (the full text of the MCP tool
descriptions and resources). What is included:
- `demo_polygon.geojson` and `long_beach_polygon.geojson`: area boundaries only.
- `long_beach_api_sample.json`: a small excerpt of the Long Beach API result.
- `result_env*.json`: small `/v1/env_params` responses, kept because they are the evidence for the `null`
  parameters and the `temperature` input test.

To reproduce scripts 04 and 05, export the heatmap layer from the dashboard as `heatmap_layer.geojson`.
Script 13 asks you to type `YES` before it spends credits.

## Not tested
The REST endpoints `/v1/satellite`, `/v1/streetview` and `/v1/heat_intelligence`; the MCP tools `report`,
`satellite` and `monitoring`; locations outside the US (the docs say they are unsupported); granularity
other than 100 m; and whether `start_time` is local time or UTC (the MCP tool description says local wall
time at the polygon; I did not test it).