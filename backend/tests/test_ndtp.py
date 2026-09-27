"""NDTP wire format and end-to-end TCP ingestion checks."""

import socket
import struct
import time
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app, ndtp_server, prediction_service
from app.services.ndtp_service import MOSCOW, NdtpProtocolError, crc16_modbus, decode_frame


def make_frame(unit_id: int, service_id: int, message_type: int, body: bytes, request_id: int = 1) -> bytes:
    payload = struct.pack("<HHHI", service_id, message_type, 1, request_id) + body
    crc = crc16_modbus(payload)
    swapped_crc = ((crc & 0xFF) << 8) | (crc >> 8)
    header = struct.pack("<HHHHBIH", 0x7E7E, len(payload), 0, swapped_crc, 2, unit_id, 0)
    return header + payload


def handshake(unit_id: int) -> bytes:
    body = struct.pack("<HHHIII", 6, 2, 0, unit_id, 65535, 0)
    return make_frame(unit_id, 0, 100, body)


def realtime(unit_id: int, timestamp: int, *, valid: bool = True) -> bytes:
    flags = 0x60 | (0x80 if valid else 0)
    nav = struct.pack(
        "<IIIBBHHHHHBB", timestamp, 376173210, 557551234,
        flags, 0, 25, 30, 90, 0, 120, 8, 2,
    )
    # The emulator can append other cells; navigation is still first.
    extra_cell = b"\x10\x00" + b"\x00" * 8
    return make_frame(unit_id, 1, 101, b"\x00\x00" + nav + extra_cell, request_id=2)


def test_decode_and_reject_bad_crc():
    unit_id = 1166336
    frame = handshake(unit_id)
    assert decode_frame(frame[:15], frame[15:]) == (unit_id, 100, None)
    frame = realtime(unit_id, 1767670500)
    parsed_unit, message_type, telemetry = decode_frame(frame[:15], frame[15:])
    assert (parsed_unit, message_type) == (unit_id, 101)
    assert telemetry.longitude == pytest.approx(37.617321)
    assert telemetry.latitude == pytest.approx(55.7551234)
    assert telemetry.speed == 25
    assert telemetry.location_valid is True

    corrupt = frame[:-1] + bytes([frame[-1] ^ 1])
    with pytest.raises(NdtpProtocolError, match="CRC"):
        decode_frame(corrupt[:15], corrupt[15:])


def test_tcp_packet_reaches_dashboard(monkeypatch):
    async def fake_prediction(context):
        return {"predicted_delay_s": 130.0, "delay_probability": 0.82,
                "reason_factors": [{"feature": "speed_now", "label": "Скорость", "value": 25,
                                    "shapValueSec": 12.0}]}

    monkeypatch.setattr(prediction_service, "predict", fake_prediction)
    original_port = ndtp_server.port
    ndtp_server.port = 0
    try:
        with TestClient(app) as client:
            unit_id = 1166336
            tr_id = "ndtp-test-vehicle"
            now = datetime.now(MOSCOW).replace(tzinfo=None, microsecond=0)
            target = now + timedelta(minutes=12)
            assert client.post("/api/v1/ndtp/units", json={"unit_id": unit_id, "tr_id": tr_id}).status_code == 200
            assert client.post("/api/v1/schedule", json={
                "tr_id": tr_id, "stop_id": "ndtp-stop", "time_begin": target.isoformat(),
                "longitude": 37.62, "latitude": 55.76,
            }).status_code == 200
            assert client.post("/api/v1/prediction-context", json={
                "tr_id": tr_id, "target_stop_id": "ndtp-stop", "current_time": now.isoformat(),
                "target_time_begin": target.isoformat(), "cur_dev_s": 30,
            }).status_code == 200

            before = client.get("/api/v1/ndtp/status").json()["received_packets"]
            with socket.create_connection(("127.0.0.1", ndtp_server.port), timeout=2) as stream:
                packet = handshake(unit_id) + realtime(
                    unit_id, int(now.replace(tzinfo=MOSCOW).timestamp())
                )
                stream.sendall(packet[:7])
                time.sleep(0.02)
                stream.sendall(packet[7:])
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline:
                    status = client.get("/api/v1/ndtp/status").json()
                    if status["received_packets"] > before:
                        break
                    time.sleep(0.02)
                assert status["received_packets"] == before + 1
                assert status["predictions_updated"] >= 1

            dashboard = client.get("/api/dashboard").json()
            assert dashboard["source"] == "backend-live"
            record = next(item for item in dashboard["records"] if item["vehicleId"] == tr_id)
            assert record["position"] == pytest.approx([37.617321, 55.7551234])
            assert record["predictionSec"] == 130.0
            assert record["riskLevel"] == "high"
            assert record["delayProbability"] == 0.82
            assert record["reasonFactors"][0]["feature"] == "speed_now"
            assert record["estimatedArrival"] is not None
    finally:
        ndtp_server.port = original_port
