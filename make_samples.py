"""Create a small excerpt of result_lb.json (the full file is too large to commit)."""
import json

b = json.load(open("result_lb.json"))
r = b["data"]["result"]
sample = {
    "activity_id": b["data"]["activity_id"],
    "stats_data": {"temperature_stats": r["stats_data"]["temperature_stats"]},
    "map_data_first_3_tiles": r["map_data"]["features"][:3],
}
json.dump(sample, open("long_beach_api_sample.json", "w"), indent=2)
print("saved long_beach_api_sample.json")