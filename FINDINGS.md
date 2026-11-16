# Findings: Temperature Dashboard, Temperature API and MCP

**Author:** Mohamed Ashraf (Data Engineering internship application)
**Test period:** Nov 11-15, 2026
**Repository:** this repo. Each finding names the script that reproduces it. Every script starts with a docstring (question, input, observed result, credit cost).

## Summary

- **The core data is consistent.** For a heatmap I created in the dashboard (Long Beach, 2022-03-16), the REST API and the MCP server return the same grid and the same statistics as the dashboard: 2,397 tiles, matching min/max/mean, and REST and MCP agree to 15 decimals.
- **The dashboard's statistics panel disagrees with its own data.** The standard deviation shown is 0.21; the tiles, the API and the panel's own box plot give about 0.12. The generated text describes histogram bins as if they were values.
- **Three things I could not reproduce or explain:** the California demo (13.8-38.9 °C) cannot be reproduced through the API; `env_params` returned 9 of 15 parameters as `null` for a 2022 date but all 15 for a 2025 date, with the same charge; and the `temperature` input is not validated (heat index up to 70.8 °C).
- **The MCP server is well designed for agents** (prices in tool descriptions, confirmation before paid calls, `cost_credits` in every response, a free `credit_balance` tool), but the docs lag the live server: 11 tools vs 9 documented, 4 undocumented resources, and parameter and unit differences, including reversed `streetview` angles.
- **Routing:** the "Coolest" route is cooler by one metric (mean segment temperature) but accumulates about 25% more degree-minutes above 32 °C than the Fastest, because it is 4.8 minutes slower. The `dial`, `thermal` and `vs_fastest` fields are undocumented.
- **Getting started:** the demo and the "How it works" sections made the dashboard easy to learn. The official REST Quickstart example failed for me with `OUT_OF_COVERAGE`, while the MCP example worked first time.

## How I evaluated

I treated the API like a new data source at work: run the official example, compare its output with the dashboard, validate the data for internal consistency, and probe edge cases. I used a Premium key (1,000,000 credits) and spent 73,660 credits (balance 926,340 at the end). That total includes one 8,600-credit `streetview` call that Cursor ran but whose result I never saw, because my Cursor usage limit ended mid-run. I checked the balance with the free `credit_balance` tool at several points, and every other charge matched the documented price.

I used the REST API for most tests, and the MCP server through Cursor and, after Cursor's limit ran out, through a direct Python client. I do not have a climate background, so I focused on data quality, schema and documentation, not model accuracy. I only state conclusions I could test. What I only read in the docs or in tool descriptions is marked "(read, not tested)".

## What works well

- The async flow (submit, poll, `completed`) is clear, and the coverage error is structured (`code`, `field`, `message`).
- Missing values are `null`, never `-999`, in every response I received. Timestamps carry a timezone offset (`America/Los_Angeles`, -07:00 on 2022-03-16).
- The heatmap results are internally clean. In the 12,363-tile result I validated: no nulls, unique `tile_id`, `min <= avg <= max` in every tile, tiles about 101 m wide.
- Speed: 30 s for a 24 km² heatmap, 104 s for 123.6 km², about 5 s for `env_params`, 34 s for a route.
- The MCP example in the docs (Phoenix, `env_params`) worked first time, and the MCP design has several good agent-safety features (see finding 6).

## Findings, most important first

### 1. Long Beach: dashboard, REST API and MCP agree (positive)

- **What I did:** I created a heatmap in the dashboard (Long Beach, 2022-03-16, single day, 100 m, 23.85 km²), exported its polygon and heatmap layer, and sent the same polygon to `POST /v1/heatmap` (`filter_type=3`) and, through the MCP, to `heatmap`. Activities: REST `daf472d3-f282-4552-9640-8140f9102851`, MCP `8ec13f14-2d6b-48f1-8107-25039d83bcdf`.
- **What I found:**
  - Same grid: 2,397 tiles, and the first corner of tile 0 is identical.
  - API min/max/mean = 17.5688 / 18.1553 / 17.9113 °C; the dashboard panel shows 17.57 / 18.16 / 17.91.
  - The exported layer has 24 hourly values per tile (57,528 rows = 2,397 x 24). The API's `average_temperature` equals the per-tile 24 h mean (max difference 0.0002 °C), `min_temperature` matches exactly, and `max_temperature` differs by up to 0.16 °C in some tiles (cause unknown).
  - `heatmap_read` on the REST and the MCP activities returns identical statistics to 15 decimals.
- **Gaps in the docs:**
  - The REST docs say `tcm` returns "temperature per tile", but not that `filter_type=3` returns a 24 h mean plus min and max, nor the tile fields (`tile_id`, `average_temperature`, `min_temperature`, `max_temperature`). I inferred them from the response.
  - The dashboard panel does not say that its min/max are statistics of daily means (the hourly values in the layer range from 12.6 to 24.9 °C).
  - The REST docs and the dashboard do not say what kind of temperature a heatmap shows. The MCP `units` resource calls it "area mean surface temperature".
- **Reproduce:** `03_long_beach_submit.py`, `04_validate_dashboard_layer.py`, `05_hourly_vs_api.py`, `12_mcp_descriptions_and_resources.py`.

### 2. Dashboard statistics panel: standard deviation and generated text

- **What I found:**
  - The panel shows SD 0.21. Computed from the 2,397 tile means it is 0.1193, which is exactly what the API and the MCP return. The panel's own box plot (IQR 0.16) implies about 0.12 too.
  - The bar-graph text gives the range as 17.78-18.33 °C, but the real range is 17.57-18.16 (those look like bin edges). "Most frequent temperature 17.78 °C, 2,072 times" is a bin count, not a value. The graph has only two bins (2,072 + 325 = 2,397), so "highly skewed" partly comes from the binning.
  - The normal-curve text says temperatures are evenly distributed around the mean, but that curve is fitted from the mean and SD, so it cannot show symmetry. The box plot quartiles are not symmetric (median - Q1 = 0.03, Q3 - median = 0.13).
  - The dashboard shows a "Heatmap Accuracy Index" (7 tiers). I found no equivalent in the API result, which only has `map_data` and `stats_data`.
- **Suggestion:** show real min/max in the text, use more bins, and check how the SD is computed.
- **Reproduce:** `05_hourly_vs_api.py`.

### 3. The California demo cannot be reproduced through the API

- **What I did:** The demo (2022-01-20, 100 m, 163.08 km², about 63 mi²) shows 13.8-38.9 °C. The API rejected it: "Heatmap size exceeds current model limit of 50 mi² / 129.5 km²" (the docs give 10 mi² for Basic and 50 mi² for Premium). I scaled the polygon to 87% around its centre (123.6 km²) and sent it with `filter_type=3`. Activity `f2058706-1a74-4710-9c7f-b770a737d9f7`.
- **What I found:** 12,363 tiles, 13.63-14.70 °C (mean 14.27, SD 0.20). No tile has `max_temperature` above 23.9 °C, so no field in the response matches the demo's 38.9 °C. The same tests on the Long Beach heatmap (finding 1) agree, so the difference may be specific to the demo.
- **Open question:** Is the demo built from the same model and data? `heatmap_read` returns `null` for the demo's ID (finding 7), and I did not download the demo's layer, so I cannot say whether 38.9 °C appears in its own tiles.
- **Suggestion:** a demo that can be reproduced through the API, and a note whenever a dashboard map is larger than the API limit.
- **Reproduce:** `02_la_demo_scaled.py`, `02b_validate_la_result.py`.

### 4. `env_params`: charged for a mostly empty result, and the docs do not say which dates are covered

- **What I found:** For Long Beach on 2022-03-16 (activity `1dbe125f-6822-486e-8af5-d9f312752fc0`), 9 of 15 parameters (all AQI values, methane, CO2) were `null` for all 24 hours. The status was `completed`, the full 2,900 credits were charged, and the response gives no reason. For the same coordinates on 2025-09-20 (activity `291af949-1f1d-498c-af22-5e743782fce6`), all 15 parameters had values. A Phoenix call through the MCP for 2025-09-20 also returned AQI, methane and CO2 values. So in my tests the nulls depend on the date, not the location; I tested two dates only, so I do not know where the cut-off is.
- **Why it matters:** 2022-03-16 is after the documented historical start for these tools (2021-01-01 in the MCP descriptions, 2019-01-01 in the REST docs), yet AQI and gases were missing. The docs only say that availability "varies by location, date and parameter".
- **Suggestion:** a coverage table by date in the docs, a per-parameter reason code in the response, and a reduced charge (or a flag) when most of the result is empty.
- **Reproduce:** `06_env_params.py`, `11_env_params_date_test.py`.

### 5. `env_params`: the `temperature` input is not validated

- **What I did:** Same location and date as finding 4, with `temperature` = 10, 17.9 and 35. Activities: `cd46eada-d6ba-4377-9fe1-7fc96d2a0260` (10), `1dbe125f-6822-486e-8af5-d9f312752fc0` (17.9), `64104dc2-0272-4b33-b266-8ad0a193095c` (35).
- **What I found:**
  - `temperature` only changes `heat_index_celsius`. Apparent temperature, wet-bulb, humidity and cloud cover were identical in all three runs.
  - At 35 the heat index ranged from 33.1 to 70.8 °C, while the apparent temperature in the same response stayed at 12-20 °C, with no error or warning.
  - A hand calculation with the standard NWS heat-index regression at 95 °F and 99% humidity gives about 70.8 °C, so the endpoint seems to apply the formula without checking its valid range.
  - The same pattern appeared through the MCP for Phoenix with a 35 °C input: heat index 33.7-44.7 °C against apparent temperature 28.8-39.7 °C. My hand calculation for 35 °C at the day's highest humidity (59.4%) gives about 44.8 °C.
  - One input value is applied to all 24 hours.
- **Docs:** the MCP tool description says `heat_index_celsius` is derived from the supplied temperature and relative humidity. The REST docs do not say this. The REST response has no `warnings` field. The MCP `data_quality` resource says implausible temperatures (outside -15 to 60 °C) are flagged in `result.warnings`; I did not test whether that applies to the heat index.
- **Suggestion:** validate the input against the weather data or return a `warnings` field, and state in the REST docs which parameters depend on the input.
- **Reproduce:** `07_env_params_input_sweep.py` (evidence: `result_env.json`, `result_env_10.json`, `result_env_35.json`).

### 6. MCP server: what works well

- Tool descriptions tell the agent to show the exact parameters and the credit cost and to ask for confirmation before paid calls, and never to invent a temperature. Cursor did exactly this.
- Every response includes `trace.cost_credits`; `credit_balance` is free; `heatmap` has an `idempotency_key`.
- Billing matched the prices in the tool descriptions at every checkpoint (except the call I did not see, see "How I evaluated").
- Cursor and the Python client returned identical results for the same `streetview` request (finding 8).
- **Reproduce:** `09_mcp_connection_check.py`, `10_mcp_inspect_tools.py`.

### 7. MCP server: docs vs the live server (read from the schemas and tool descriptions; differences marked "tested" were run)

- **Tools:** the docs list 9 tools; the server exposes 11 (`credit_balance` and `monitoring` are extra; I did not test `monitoring`). It also exposes 4 resources (`coverage`, `units`, `data_quality`, `entitlements`) that the docs do not mention. They are useful, and the `units` resource answers a question the REST docs leave open (finding 1).
- **Report temperature unit:** the live `report` schema asks for degrees Fahrenheit. The MCP docs page says Celsius, and the REST docs page contradicts itself (the `temperature` field says Fahrenheit, the `date` field mentions a Celsius temperature). Not tested.
- **Report analyses:** the docs say 1-5 analysis types; the live schema says Premium allows at most 2.
- **`wait_for_completion`:** documented for `heatmap`, `report` and `temperature_routing`, but it is not in any live schema. Cursor polled `heatmap_read` itself.
- **`map_type`:** documented as an input; the live schema says it is accepted but ignored.
- **Granularity:** the REST docs allow 20/60/80/100 m; the MCP allows 60/80/100.
- **Earliest date:** the REST docs say 2019-01-01; the MCP tool descriptions say 2021-01-01 for heatmap, `env_params` and report (2019-01-01 for satellite).
- **Inputs only in the live schema:** `heatmap_id`, `idempotency_key`, `notify_by_email`, `threshold`, `direction`.
- **Silent null (tested):** `heatmap_read` is described as usable for heatmaps "already shown in Dashboard". I called it with the dashboard IDs of the California demo (`f5b3844f-0df6-4fbf-9ab2-9f5754ed5d3b`) and of my Long Beach map (`f3029bd3-b4a7-4b41-ab74-c6e56227cf0b`). Both returned `value: null` with HTTP 200, no error and no warning, while API-created activities were read correctly. I do not know whether this is expected; a "not found" error would be clearer than a silent null.
- **Reproduce:** `10_mcp_inspect_tools.py`, `12_mcp_descriptions_and_resources.py`.

### 8. `streetview`: angle parameters are described the opposite way in the docs

- **What the docs and the schema say:** the docs page describes `vertical_angle` as tilt and `horizontal_angle` as a 0-360 degree pan. The live schema says `vertical_angle` is the heading (the back view uses heading + 180) and `horizontal_angle` is a pitch control divided by 100 (100 gives 1 degree), with no range enforced.
- **What I tested** (point 33.8166, -118.1083, `back_view=false`):

| Class | v=0, h=0 | v=0, h=90 | v=90, h=0 |
|---|---|---|---|
| Tree | 40.81% | 41.27% | 7.42% |
| Road | 33.02% | 33.11% | 22.79% |
| Sky | 8.71% | 9.02% | 38.68% |
| Building | 1.80% | 1.85% | 12.52% |
| House | not reported | not reported | 14.90% |

- **What I found:** changing `horizontal_angle` from 0 to 90 moved every class by less than 1 percentage point, while `vertical_angle` 90 changed the scene completely. The first two runs were made through Cursor; repeating the v=0, h=0 request with a Python client gave identical percentages, so the small `horizontal_angle` effect is real and not noise. The results match the live schema, not the docs page. Image date for the Python runs: 2022-08-01.
- **Suggestion:** fix the docs page, and consider renaming the parameters (`heading` and `pitch`) and enforcing ranges.
- **Reproduce:** `13_mcp_streetview_and_routing.py streetview` and `streetview-repeat`.

### 9. `temperature_routing`

- **What I did:** two points in the Greater Los Angeles area (33.7701, -118.1937 to 33.9401, -118.1332), departure 2026-11-15T14:00:00-08:00, through the Python MCP client. Activity `028940c1-380c-4def-86d4-74d82812e7da`. Cost 3,500 credits.
- **What I found:** 3 routes about 34 s after submitting (I polled every ~6 s). The thermal values come from `result_routing.json` (kept local):

| Label | Distance | Duration | `mean_c` | `time_weighted_c` | `dist_weighted_c` | Degree-minutes above 32 °C |
|---|---|---|---|---|---|---|
| Fastest (selected) | 23.285 km | 18.17 min | 38.083 | 37.683 | 37.652 | 103.28 |
| Balanced | 22.846 km | 20.31 min | 37.968 | 37.714 | 37.681 | 116.05 |
| Coolest | 22.614 km | 22.94 min | 37.735 | 37.641 | 37.674 | 129.40 |

- **"Coolest" depends on the metric.** Against the Fastest route it is cooler by 0.348 °C in `mean_c` (the basis of `vs_fastest.mean_temp_delta_c`), but only 0.04 °C cooler in `time_weighted_c`, and 0.02 °C warmer in `dist_weighted_c`.
- **Cumulative exposure is higher on the "Coolest" route.** Every route is above the 32 °C threshold for its whole duration (`minutes_above_threshold` equals the duration). The reported `degree_minutes_above_threshold` matches duration x (`time_weighted_c` - 32) in my check (for example 22.94 x 5.641 = 129.4), so the "Coolest" route accumulates about 25% more degree-minutes than the Fastest (129.4 vs 103.28), because it takes 4.77 min (26%) longer. All three routes share the same `peak_c` of 39.16 °C.
- **Undocumented fields:** `dial` (`positions` [10, 5, 1], `n_candidates` 5, `best_delta_min` 4.77, `best_delta_c` -0.348, `span_pct` 26.25, `requested_score` null), `thermal`, and `vs_fastest` (including `jaccard`, which looks like a route-overlap measure: 0.26 for the Coolest route). The docs only mention "thermal metrics" and "route preference metadata".
- **Open question:** an average of about 38 °C on a mid-November afternoon in Los Angeles is well above typical air temperatures there. The docs do not say which kind of temperature routing uses (air or surface) or its source (observed, forecast or model). I did not check this. (The MCP `units` resource calls the heatmap temperature a surface temperature.)
- **Inputs:** the tool only takes origin, destination and departure time, so the caller cannot choose what to optimise; the graph is a driving network (read, not tested).
- **Suggestion:** define what "Coolest" means (which metric), consider cumulative exposure as the ranking or as an option, document the `dial`, `thermal` and `vs_fastest` fields, state the temperature kind and source, and let the caller choose the priority (heat, time or distance, fuel). I cannot judge fuel use from this one example.
- **Reproduce:** `13_mcp_streetview_and_routing.py routing`.

### 10. Connecting Cursor on Windows

- The Client Setup page only shows `export` (Mac/Linux) commands, with no PowerShell example.
- With the configuration from the docs, Cursor showed `401 invalid_token` until I launched it from a PowerShell window where `FORTYGUARD_API_KEY` was set. My interpretation is that the variable was not visible to Cursor when launched normally.
- The 401 message advises "clear authentication tokens in your MCP client and re-register", which is OAuth advice, although the server uses a static API key. A Python script (`09_mcp_connection_check.py`) showed the server accepts my key (11 tools) and returns the identical message for a deliberately invalid key. So the message does not tell a missing key from an invalid one, and I only found the cause by testing outside Cursor.
- One early `credit_balance` call through Cursor timed out and worked on retry.
- **Suggestion:** a PowerShell snippet, a note that GUI clients need the variable at launch, and a 401 message that says "Authorization header missing or empty" separately from "key invalid".

### 11. Documentation and onboarding gaps (REST)

- **The official Quickstart example fails.** The REST example (Lower Manhattan, 2024-07-15 14:00, `filter_type=1`) returned `400 OUT_OF_COVERAGE` on `polygon_aoi`. The message says the location is outside supported U.S. coverage, but Lower Manhattan is in the U.S., so the cause may be the date or the hour; I did not isolate it. The docs have no coverage table. The MCP example, in contrast, worked. Reproduce: `01_quickstart_official_example.py`.
- **Error shapes differ:** the coverage error has `code`, `field` and `status_code`; the area-limit error has only `error` and `message`.
- **`solar_irradiance`:** the docs describe time-aligned arrays; the response is one clear-sky daytime average (GHI 516.42, DNI 665.21, DHI 106.26 W/m² for Long Beach 2022-03-16) with a text description. Clear-sky values ignore the cloud cover returned in the same response (up to 8 octas that day). Reproduce: `08_inspect_solar.py`.
- **Field names:** the docs use capital letters (`Temperature_stats`, `Minimum`); the responses use lowercase (`temperature_stats`, `minimum`).
- **Status values:** the docs mix `Completed` and `completed`/`succeeded`. My code lowercased the status, so I did not check the real casing.
- **Read from the docs, not tested:** in Heat Intelligence the `temperature` field is described as Fahrenheit while `date` mentions a Celsius temperature; the Satellite output has a misspelled `orignal_image` field (the docs call it a legacy alias).

### 12. Dashboard experience as a new user

**What helped me most**
- **A ready-made demo with a guided walkthrough.** I could start without help.
- **The "How it works" section in each tool.** It explained what each tool does. I used it to build my own heatmaps modelled on the demo, and the same parameters (date, time frame, granularity, area) mapped directly onto the API request, so moving from the dashboard to the API was easy.
- **Clear messages when an option is unavailable.** I created a single-hour heatmap and expected Time Series Simulation to work. The dashboard told me it is only available for "Range of Hours", "Single Day", "Range of Days" or "Single Month" heatmaps. That was my mistake, and the message made the cause obvious.
- **"Find the Coolest Route".** It returns several routes, gives details for each and marks the best one. It feels like a familiar maps app with more information, and I liked it a lot.

**Where I got stuck**
- **Route calculation time.** A route of about 20 km took a bit over a minute to appear (I did not time it exactly), compared with under 10 seconds in Google Maps. I understand it also computes heat exposure, so some difference is expected. *Suggestion:* show a progress indicator or an expected time.

**Suggestions**
- **Let the user choose how routes are sorted.** Results are always "sorted by heat exposure". I wanted to also sort by travel time or distance, or by estimated fuel use: not everyone drives an electric car, and drivers who want to save fuel may prefer a different route than the coolest one.
- **Coverage.** The dashboard is limited to the US. I had hoped to try my own region, and would have loved the route tool there. The email explained this, so it was not a surprise, only a limit.

### 13. Account and onboarding

- The dashboard's first form requires a US state, with no option for users outside the US (I am not in the US, so I picked one).
- The email says "Free plan", but the account is Premium (one-time, 1,000,000 credits, expiring Nov 18).
- A temporary password was sent in plain text in the email; a set-password link would be safer.

## Suggested priorities

1. **Dashboard and API consistency:** a demo that can be reproduced through the API, and a correct SD and generated text in the statistics panel.
2. **`env_params`:** per-parameter reason codes, a coverage-by-date table, and validation of the `temperature` input.
3. **Keep the MCP docs in sync with the server:** tools, resources, units, and the `streetview` angles.
4. **Quickstart and error messages:** a Quickstart example that works, and clearer 401 and `OUT_OF_COVERAGE` messages.
5. **Routing:** define what "Coolest" means (the label depends on the metric: mean segment temperature, time-weighted temperature or cumulative exposure), document the `dial`, `thermal` and `vs_fastest` fields, and let the caller choose the priority.

## Not tested

The REST endpoints `/v1/satellite`, `/v1/streetview` and `/v1/heat_intelligence`; the MCP tools `report`, `satellite` and `monitoring`; Time Series Simulation and other dashboard tools beyond heatmaps and routing; locations outside the US (the docs say they are unsupported); granularity other than 100 m; and whether `start_time` is local time or UTC (the MCP tool description says local wall time at the polygon).