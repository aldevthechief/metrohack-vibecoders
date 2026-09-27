from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app, ndtp_server, prediction_context_service, prediction_service
from app.services.schedule_service import ScheduleService


def test_plan_csv_and_prediction_window():
    service = ScheduleService()
    plan = Path(__file__).resolve().parents[2] / "dataset" / "validate" / "schedule_plan.csv"
    assert service.load_plan_csv(plan) == 5558
    target = service.get_next_target("131672", datetime.fromisoformat("2026-01-06 03:35:00"))
    assert target.stop_id == "53700172828"
    assert target.time_begin == datetime.fromisoformat("2026-01-06 03:50:00")
    # The left boundary is open, the right boundary is closed.
    assert service.get_next_target("131672", datetime.fromisoformat("2026-01-06 03:40:00")).stop_id != target.stop_id


def test_startup_loads_schedule_and_unit_context(monkeypatch, tmp_path):
    plan = tmp_path / "schedule.csv"
    plan.write_text(
        "tr_id,tt_action_item_id,time_begin,geom,building_address\n"
        'startup-vehicle,startup-stop,2026-01-06 12:12:00,"POINT (37.6 55.75)",Example\n',
        encoding="utf-8",
    )
    units = tmp_path / "units.csv"
    units.write_text("unit_id,tr_id,cur_dev_s\n123456,startup-vehicle,41\n", encoding="utf-8")
    monkeypatch.setenv("SCHEDULE_PLAN_PATH", str(plan))
    monkeypatch.setenv("NDTP_UNITS_PATH", str(units))
    original_port = ndtp_server.port
    ndtp_server.port = 0
    try:
        with TestClient(app) as client:
            schedule = client.get("/api/v1/schedule/startup-vehicle").json()
            assert len(schedule) == 1
            assert schedule[0]["stop_id"] == "startup-stop"
            assert client.get("/api/v1/ndtp/status").json()["unit_map"]["123456"] == "startup-vehicle"
            assert prediction_context_service.get_current_deviation("startup-vehicle") == 41
    finally:
        ndtp_server.port = original_port


def test_telemetry_selects_new_target_without_target_context(monkeypatch):
    async def fake_prediction(context):
        return {"predicted_delay_s": context.cur_dev_s + 10}

    monkeypatch.setattr(prediction_service, "predict", fake_prediction)
    client = TestClient(app)
    tr_id = "auto-target-test-vehicle"
    for stop_id, time_begin in (("prior", "2026-01-06 12:01:00"),
                                ("first", "2026-01-06 12:12:00"),
                                ("second", "2026-01-06 12:17:00")):
        response = client.post("/api/v1/schedule", json={
            "tr_id": tr_id, "stop_id": stop_id, "time_begin": time_begin,
            "longitude": 37.6, "latitude": 55.75,
        })
        assert response.status_code == 200
    assert client.post("/api/v1/current-deviation", json={"tr_id": tr_id, "cur_dev_s": 42}).status_code == 200

    for current_time in ("2026-01-06 12:00:00", "2026-01-06 12:05:00"):
        if current_time.endswith("12:05:00"):
            response = client.post("/api/v1/arrivals", json={
                "tr_id": tr_id, "stop_id": "prior", "actual_time": "2026-01-06 12:03:00",
            })
            assert response.status_code == 200
            assert response.json()["cur_dev_s"] == 120
        response = client.post("/api/v1/telemetry", json={
            "tr_id": tr_id, "event_time": current_time, "receive_time": current_time,
            "speed": 15, "location_valid": True, "longitude": 37.59, "latitude": 55.74,
        })
        assert response.status_code == 200
        assert response.json()["prediction_updated"] is True

    records = [item for item in client.get("/api/dashboard").json()["records"] if item["vehicleId"] == tr_id]
    assert [item["targetStopId"] for item in records] == ["first", "second"]
    assert [item["predictionSec"] for item in records] == [52, 130]
