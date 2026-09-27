from fastapi.testclient import TestClient

from app.main import app, prediction_service


def test_gps_stop_arrival_updates_deviation_and_dashboard(monkeypatch):
    async def fake_prediction(context):
        return {"predicted_delay_s": context.cur_dev_s + 10}

    monkeypatch.setattr(prediction_service, "predict", fake_prediction)
    client = TestClient(app)
    tr_id = "gps-arrival-test-vehicle"
    for stop_id, time_begin, lon, lat in (
        ("previous", "2026-01-06 12:01:00", 37.6, 55.75),
        ("target", "2026-01-06 12:14:00", 37.62, 55.76),
    ):
        response = client.post("/api/v1/schedule", json={
            "tr_id": tr_id, "stop_id": stop_id, "time_begin": time_begin,
            "longitude": lon, "latitude": lat,
        })
        assert response.status_code == 200

    for index, second in enumerate((0, 6, 12)):
        event_time = f"2026-01-06 12:02:{second:02d}"
        response = client.post("/api/v1/telemetry", json={
            "tr_id": tr_id, "packet_id": f"gps-{index}",
            "event_time": event_time, "receive_time": event_time,
            "speed": 1, "location_valid": True,
            "longitude": 37.60005, "latitude": 55.75002,
        })
        assert response.status_code == 200
        assert response.json()["prediction_updated"] is (index == 2)

    record = next(item for item in client.get("/api/dashboard").json()["records"]
                  if item["vehicleId"] == tr_id)
    assert record["currentDeviationSec"] == 60
    assert record["currentDeviationSource"] == "gps-estimate"
    assert record["predictionSec"] == 70


def test_single_or_fast_gps_fix_is_not_an_arrival(monkeypatch):
    async def fake_prediction(context):
        return {"predicted_delay_s": context.cur_dev_s}

    monkeypatch.setattr(prediction_service, "predict", fake_prediction)
    client = TestClient(app)
    tr_id = "gps-arrival-fast-vehicle"
    client.post("/api/v1/schedule", json={
        "tr_id": tr_id, "stop_id": "previous", "time_begin": "2026-01-06 12:01:00",
        "longitude": 37.6, "latitude": 55.75,
    })
    for index, speed in enumerate((1, 20, 1)):
        event_time = f"2026-01-06 12:02:{index * 6:02d}"
        response = client.post("/api/v1/telemetry", json={
            "tr_id": tr_id, "event_time": event_time, "receive_time": event_time,
            "speed": speed, "location_valid": True,
            "longitude": 37.6, "latitude": 55.75,
        })
        assert response.status_code == 200
        assert response.json()["prediction_updated"] is False
