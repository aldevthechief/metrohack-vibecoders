"""Build a small, reproducible frontend replay from the supplied validate data.

Only telemetry at or before each prediction timestamp is used. No validate labels
or future factual schedule fields are read.
"""

from __future__ import annotations

import bisect
import csv
import json
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
ROOT = REPO.parent
DATASET_ROOT = next((path for path in (ROOT / "dataset", REPO / "dataset") if path.exists()), ROOT / "dataset")
DATASET = DATASET_ROOT / "validate"
SUBMISSION = next((path for path in (ROOT / "submission.csv", REPO / "submission.csv") if path.exists()), ROOT / "submission.csv")
OUTPUT = Path(__file__).resolve().parents[1] / "src" / "data" / "demo.json"


def rows(path: Path, delimiter: str = ","):
    with path.open(encoding="utf-8", newline="") as stream:
        yield from csv.DictReader(stream, delimiter=delimiter)


def point(geom: str):
    if not geom or not geom.startswith("POINT ("):
        return None
    try:
        lon, lat = geom[7:-1].split()
        return [round(float(lon), 7), round(float(lat), 7)]
    except ValueError:
        return None


def is_valid_location(row):
    try:
        lon, lat = float(row["lon"]), float(row["lat"])
        return row["location_valid"].lower() == "true" and 36.5 < lon < 38.5 and 55 < lat < 56.5
    except (TypeError, ValueError):
        return False


def main():
    predictions = {
        row["sample_id"]: float(row["prediction"])
        for row in rows(SUBMISSION, ";")
    }
    schedule = defaultdict(list)
    stops = {}
    for row in rows(DATASET / "schedule_plan.csv"):
        stop = {
            "id": row["tt_action_item_id"],
            "time": row["time_begin"],
            "address": row["building_address"],
            "coordinate": point(row["geom"]),
        }
        schedule[row["tr_id"]].append(stop)
        stops[stop["id"]] = stop
    for vehicle_stops in schedule.values():
        vehicle_stops.sort(key=lambda item: item["time"])

    traffic = defaultdict(list)
    for row in rows(DATASET / "traffic.csv"):
        if is_valid_location(row):
            traffic[row["tr_id"]].append(row)
    times = {}
    for vehicle_id, vehicle_traffic in traffic.items():
        vehicle_traffic.sort(key=lambda item: item["event_time"])
        times[vehicle_id] = [item["event_time"] for item in vehicle_traffic]

    records = []
    for row in rows(DATASET / "points.csv"):
        vehicle_id = row["tr_id"]
        now = datetime.fromisoformat(row["T"])
        target = datetime.fromisoformat(row["target_time_begin"])
        target_stop = stops.get(row["target_stop_id"], {})
        target_index = next((i for i, stop in enumerate(schedule.get(vehicle_id, [])) if stop["id"] == row["target_stop_id"]), None)
        previous_named_stop = next((stop for stop in reversed(schedule[vehicle_id][:target_index]) if stop["address"] and target - datetime.fromisoformat(stop["time"]) <= timedelta(minutes=30)), None) if target_index is not None else None
        segment_label = (
            f"{previous_named_stop['address']} → {target_stop['address']}"
            if previous_named_stop and target_stop.get("address")
            else f"До остановки № {row['target_stop_id']}"
        )
        vehicle_traffic = traffic.get(vehicle_id, [])
        index = bisect.bisect_right(times.get(vehicle_id, []), row["T"] + ".999999")
        last = vehicle_traffic[index - 1] if index else None
        age = round((now - datetime.fromisoformat(last["event_time"])).total_seconds()) if last else None
        recent = [
            item for item in vehicle_traffic[max(0, index - 100):index]
            if datetime.fromisoformat(item["event_time"]) >= now - timedelta(minutes=4)
        ]
        speeds = [float(item["speed"]) for item in recent if item["speed"]]
        mean_speed = sum(speeds) / len(speeds) if speeds else None
        stop_fraction = sum(speed < 4 for speed in speeds) / len(speeds) if speeds else None
        if age is None or age > 300:
            signal = "Нет актуальной телеметрии"
        elif stop_fraction is not None and stop_fraction >= 0.6:
            signal = "Длительный простой"
        elif mean_speed is not None and mean_speed < 12:
            signal = "Низкая скорость"
        elif float(row["cur_dev_s"]) > 120:
            signal = "Уже есть отклонение"
        else:
            signal = "Явного сигнала нет"

        route = [
            stop for stop in schedule.get(vehicle_id, [])
            if now - timedelta(minutes=20) <= datetime.fromisoformat(stop["time"]) <= target + timedelta(minutes=8)
            and stop["coordinate"]
        ]
        if target_stop.get("coordinate") and target_stop not in route:
            route.append(target_stop)
            route.sort(key=lambda item: item["time"])
        if len(route) > 22:
            route = route[-22:]

        trail = [
            [round(float(item["lon"]), 7), round(float(item["lat"]), 7)]
            for item in recent[:: max(1, len(recent) // 20)]
        ]
        records.append({
            "sampleId": row["sample_id"],
            "vehicleId": vehicle_id,
            "timestamp": row["T"],
            "targetTime": row["target_time_begin"],
            "targetStopId": row["target_stop_id"],
            "targetAddress": target_stop.get("address") or "Адрес остановки не указан",
            "segmentLabel": segment_label,
            "targetCoordinate": target_stop.get("coordinate"),
            "position": [round(float(last["lon"]), 7), round(float(last["lat"]), 7)] if last else None,
            "telemetryTime": last["event_time"] if last else None,
            "telemetryAgeSec": age,
            "speedKmh": round(float(last["speed"]), 1) if last and last["speed"] else None,
            "meanSpeedKmh": round(mean_speed, 1) if mean_speed is not None else None,
            "stopFraction": round(stop_fraction, 2) if stop_fraction is not None else None,
            "currentDeviationSec": float(row["cur_dev_s"]),
            "predictionSec": round(predictions[row["sample_id"]], 1),
            "horizonSec": round((target - now).total_seconds()),
            "signal": signal,
            "route": [stop["coordinate"] for stop in route],
            "trail": trail,
        })

    records.sort(key=lambda item: (item["timestamp"], item["vehicleId"]))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps({
        "source": "validate/points.csv + validate/traffic.csv + validate/schedule_plan.csv + submission.csv",
        "date": "2026-01-06",
        "records": records,
    }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {len(records)} prediction points to {OUTPUT}")


if __name__ == "__main__":
    main()
