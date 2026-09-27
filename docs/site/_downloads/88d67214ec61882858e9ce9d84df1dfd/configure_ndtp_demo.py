"""Configure one emulator unit and a temporary 10–15 minute prediction target."""

import argparse
import json
import time
from datetime import datetime, timedelta
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


def post(url: str, payload: dict) -> dict:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=10) as response:
            return json.load(response)
    except HTTPError as error:
        raise RuntimeError(f"{url}: HTTP {error.code}: {error.read().decode('utf-8')}") from error
    except URLError as error:
        raise RuntimeError(f"{url}: {error.reason}") from error


def get(url: str) -> dict:
    with urlopen(url, timeout=10) as response:
        return json.load(response)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend-url", default="http://127.0.0.1:8000")
    parser.add_argument("--emulator-url", default="http://127.0.0.1:18080")
    parser.add_argument("--unit-id", type=int, default=1166336)
    parser.add_argument("--tr-id")
    parser.add_argument("--target-host", default="host.docker.internal")
    parser.add_argument("--target-port", type=int, default=9201)
    parser.add_argument("--interval-ms", type=int, default=5000)
    parser.add_argument("--duration-minutes", type=int, default=120)
    parser.add_argument("--cur-dev-s", type=float, default=0.0)
    parser.add_argument("--verify-timeout", type=int, default=25)
    args = parser.parse_args()
    if args.duration_minutes < 12 or args.verify_timeout < 1:
        parser.error("duration-minutes must be >= 12 and verify-timeout must be >= 1")

    tr_id = args.tr_id or str(args.unit_id)
    now = datetime.now(ZoneInfo("Europe/Moscow")).replace(tzinfo=None, microsecond=0)
    backend = args.backend_url.rstrip("/")
    before = get(f"{backend}/api/v1/ndtp/status")

    post(f"{backend}/api/v1/schedule", {
        "tr_id": tr_id,
        "stop_id": f"ndtp-demo-{args.unit_id}-{int(now.timestamp())}-start",
        "time_begin": (now - timedelta(minutes=3)).isoformat(sep=" "),
        "longitude": 37.598,
        "latitude": 55.749,
        "address": "Начало демонстрационного маршрута",
    })
    stop_count = 0
    for minutes in range(12, args.duration_minutes + 1, 5):
        target = now + timedelta(minutes=minutes)
        post(f"{backend}/api/v1/schedule", {
            "tr_id": tr_id,
            "stop_id": f"ndtp-demo-{args.unit_id}-{int(now.timestamp())}-{minutes}",
            "time_begin": target.isoformat(sep=" "),
            "longitude": 37.6 + 0.002 * (stop_count % 6),
            "latitude": 55.75 + 0.001 * (stop_count % 6),
            "address": f"Демонстрационная остановка {stop_count + 1}",
        })
        stop_count += 1

    post(f"{backend}/api/v1/current-deviation", {
        "tr_id": tr_id, "cur_dev_s": args.cur_dev_s,
    })
    post(f"{backend}/api/v1/ndtp/units", {"unit_id": args.unit_id, "tr_id": tr_id})
    post(f"{args.emulator_url.rstrip('/')}/api/config", {
        "targetHost": args.target_host,
        "targetPort": args.target_port,
        "units": [{"unitId": args.unit_id, "intervalMs": args.interval_ms,
                   "autoGenerate": True, "cells": []}],
    })
    print(f"NDTP unit {args.unit_id} -> vehicle {tr_id}; {stop_count} planned stops")
    print(f"Demo initial cur_dev_s={args.cur_dev_s}; this is a supplied value, not measured by NDTP")
    print(f"Dashboard: {backend}/api/dashboard")
    print(f"Receiver status: {backend}/api/v1/ndtp/status")

    deadline = time.monotonic() + args.verify_timeout
    while time.monotonic() < deadline:
        status = get(f"{backend}/api/v1/ndtp/status")
        if status["predictions_updated"] > before["predictions_updated"]:
            dashboard = get(f"{backend}/api/dashboard")
            records = [record for record in dashboard["records"] if record["vehicleId"] == tr_id]
            if dashboard["source"] == "backend-live" and records:
                latest = records[-1]
                print(json.dumps({
                    "received_packets": status["received_packets"] - before["received_packets"],
                    "predictions_updated": status["predictions_updated"] - before["predictions_updated"],
                    "dashboard_source": dashboard["source"],
                    "sampleId": latest["sampleId"],
                    "predictionSec": latest["predictionSec"],
                    "delayProbability": latest["delayProbability"],
                    "reasonFactors": len(latest["reasonFactors"]),
                }, ensure_ascii=False))
                return
        time.sleep(1)
    raise RuntimeError("NDTP packets did not produce a dashboard prediction before timeout")


if __name__ == "__main__":
    main()
