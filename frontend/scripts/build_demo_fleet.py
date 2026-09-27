"""Sample real validation GPS tracks for the browser replay.

The track contains only valid historical telemetry. Predictions remain in
demo.json and are never invented for vehicles without a validation point.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
ROOT = REPO.parent
DATASET_ROOT = next((path for path in (ROOT / "dataset", REPO / "dataset") if path.exists()), ROOT / "dataset")
TRAFFIC = DATASET_ROOT / "validate" / "traffic.csv"
OUTPUT = Path(__file__).resolve().parents[1] / "src" / "data" / "demo_fleet.json"
SAMPLE_INTERVAL_SECONDS = 10


def main() -> None:
    tracks = defaultdict(list)
    with TRAFFIC.open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            if row["location_valid"].lower() != "true":
                continue
            try:
                lon, lat = float(row["lon"]), float(row["lat"])
                event_time = datetime.fromisoformat(row["event_time"])
            except (TypeError, ValueError):
                continue
            if not (36.5 < lon < 38.5 and 55 < lat < 56.5):
                continue
            seconds = round((event_time - event_time.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds(), 1)
            try:
                speed = round(float(row["speed"]), 1)
            except (TypeError, ValueError):
                speed = None
            tracks[row["tr_id"]].append([seconds, round(lon, 7), round(lat, 7), speed])

    sampled = {}
    for vehicle_id, points in tracks.items():
        points.sort(key=lambda point: point[0])
        kept = []
        for point in points:
            if not kept or point[0] - kept[-1][0] >= SAMPLE_INTERVAL_SECONDS:
                kept.append(point)
        if points and kept[-1] != points[-1]:
            kept.append(points[-1])
        sampled[vehicle_id] = kept

    OUTPUT.write_text(json.dumps({
        "source": "validate/traffic.csv: valid GPS sampled at most every 10 seconds",
        "date": "2026-01-06",
        "tracks": sampled,
    }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {sum(map(len, sampled.values()))} GPS points for {len(sampled)} vehicles to {OUTPUT}")


if __name__ == "__main__":
    main()
