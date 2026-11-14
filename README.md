# FortyGuard API evaluation

An independent evaluation of FortyGuard's Temperature Dashboard and Temperature API, prepared
for the product-evaluation step of my Data Engineering internship application. I treated the API
as a new data source: run the official example, compare outputs with the dashboard, validate the
data for internal consistency, and probe edge cases. I do not have a climate background, so I
focused on data quality, schema, and documentation rather than model accuracy.

All numbers come from a Premium test key, mainly one area: Long Beach, California, on 2022-03-16.

## Setup (Windows PowerShell)
```powershell
pip install -r requirements.txt
$env:FORTYGUARD_API_KEY="<your key>"   
```

## How the API works
Each request returns an `activity_id`. I poll `GET /v1/status/{activity_id}` until the status is
`completed`, and the result comes back in the same response. Credits are charged on completion.

## Scripts
Every script starts with a docstring: question, input, observed result, and credit cost.

| Script | What it does | Calls API? |
|---|---|---|
| `01_quickstart_official_example.py` | Runs the official Quickstart example | Yes (rejected, 400) |
| `02_la_demo_scaled.py` | Reproduces the dashboard's California demo through the API | Yes |
| `02b_validate_la_result.py` | Checks the LA result: nulls, unique tile ids, min <= avg <= max, tile size | No |
| `03_long_beach_submit.py` | Sends the Long Beach polygon created in the dashboard | Yes |
| `04_validate_dashboard_layer.py` | Validates the heatmap layer exported from the dashboard | No |
| `05_hourly_vs_api.py` | Compares the API result with the dashboard layer, tile by tile | No |
| `06_env_params.py` | First call to `/v1/env_params` | Yes |
| `07_env_params_input_sweep.py` | Tests how the `temperature` input affects `/v1/env_params` | Yes |
| `08_inspect_solar.py` | Inspects the `solar_irradiance` block | No |
| `make_samples.py` | Creates `long_beach_api_sample.json` | No |

## Data policy
Large raw responses (`result_la.json`, `result_lb.json`) and the dashboard's exported heatmap
layer are not committed: they are large and they are FortyGuard's data. The files that are included:
- `demo_polygon.geojson` and `long_beach_polygon.geojson`: area boundaries only.
- `long_beach_api_sample.json`: a small excerpt of the Long Beach API result.
- `result_env*.json`: small `/v1/env_params` responses, kept because they are the evidence
  for the `null` parameters and the `temperature` input test.

To reproduce scripts 04 and 05, export the heatmap layer from the dashboard as `heatmap_layer.geojson`.

## Not tested
MCP server, `/v1/satellite`, `/v1/streetview`, `/v1/heat_intelligence`, locations outside the
US, granularity other than 100 m, and whether `start_time` is local time or UTC.