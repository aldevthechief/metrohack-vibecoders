"""Run the validate stream through the backend feature builder and ML API.

The replay has its own vehicle history; historical packets never alter the live
NDTP fleet or its alerts. Validate labels and saved predictions are not read.
"""

import asyncio
import logging
from csv import DictReader
from datetime import datetime
from pathlib import Path

from app.models.schedule import PredictionContext
from app.models.telemetry import TelemetryPoint
from app.services.dashboard_service import DashboardService
from app.services.features.feature_service import FeatureService
from app.services.features.schedule_features import ScheduleFeatureService
from app.services.features.spatial_features import SpatialFeatureService
from app.services.features.telemetry_features import TelemetryFeatureService
from app.services.incident_service import IncidentService
from app.services.prediction_service import PredictionService
from app.services.schedule_service import ScheduleService
from app.services.vehicle_state_service import VehicleStateService


LOG = logging.getLogger(__name__)


class HistoricalReplayService:
    def __init__(self, schedule: ScheduleService, points_path: Path, traffic_path: Path, ml_url: str) -> None:
        self._schedule = schedule
        self._points_path = points_path
        self._traffic_path = traffic_path
        self._ml_url = ml_url
        self._task: asyncio.Task | None = None
        self._records: list[dict] = []
        self._timestamps: list[str] = []
        self.state = "idle"
        self.completed = 0
        self.total = 0
        self.error: str | None = None

    def start(self) -> dict:
        if self.state == "idle" or self.state == "failed":
            self.state = "running"
            self.completed = 0
            self.total = 0
            self.error = None
            self._records = []
            self._timestamps = []
            self._task = asyncio.create_task(self._run())
        return self.status()

    def status(self) -> dict:
        return {
            "source": "backend-replay",
            "date": "2026-01-06",
            "state": self.state,
            "completed": self.completed,
            "total": self.total,
            "error": self.error,
            "records": list(self._records),
            "timelineTimestamps": list(self._timestamps),
        }

    def _read_inputs(self):
        with self._points_path.open(encoding="utf-8", newline="") as stream:
            points = list(DictReader(stream))
        points.sort(key=lambda row: (row["T"], row["sample_id"]))
        wanted = {row["tr_id"] for row in points}
        packets = []
        with self._traffic_path.open(encoding="utf-8", newline="") as stream:
            for row in DictReader(stream):
                if row["tr_id"] not in wanted:
                    continue
                packet = TelemetryPoint(
                    packet_id=row["packet_id"], tr_id=row["tr_id"], unit_id=row["unit_id"] or None,
                    event_time=datetime.fromisoformat(row["event_time"]),
                    receive_time=datetime.fromisoformat(row["receive_time"]),
                    gps_time=datetime.fromisoformat(row["gps_time"]) if row["gps_time"] else None,
                    longitude=float(row["lon"]) if row["lon"] else None,
                    latitude=float(row["lat"]) if row["lat"] else None,
                    altitude=float(row["alt"]) if row["alt"] else None,
                    speed=float(row["speed"]) if row["speed"] else None,
                    heading=float(row["heading"]) if row["heading"] else None,
                    location_valid=row["location_valid"].lower() == "true",
                    is_hist=row["is_hist_data"].lower() == "true",
                )
                packets.append(packet)
        # A packet becomes available only after both the event and its reception.
        packets.sort(key=lambda packet: max(packet.event_time, packet.receive_time))
        return points, packets

    async def _run(self) -> None:
        try:
            points, packets = await asyncio.to_thread(self._read_inputs)
            self.total = len(points)
            self._timestamps = sorted({row["T"] for row in points})
            vehicle_state = VehicleStateService()
            features = FeatureService(
                schedule_feature_service=ScheduleFeatureService(self._schedule),
                spatial_feature_service=SpatialFeatureService(vehicle_state),
                telemetry_feature_service=TelemetryFeatureService(vehicle_state),
                schedule_service=self._schedule,
            )
            predictor = PredictionService(features, self._ml_url)
            incidents = IncidentService(features)
            dashboard = DashboardService(vehicle_state, self._schedule)
            packet_index = 0
            for row in points:
                at = datetime.fromisoformat(row["T"])
                while packet_index < len(packets) and max(packets[packet_index].event_time, packets[packet_index].receive_time) <= at:
                    vehicle_state.add(packets[packet_index])
                    packet_index += 1
                target = self._schedule.get_target(row["tr_id"], row["target_stop_id"])
                if target is None or target.time_begin != datetime.fromisoformat(row["target_time_begin"]):
                    raise ValueError(f"No matching plan for {row['sample_id']}")
                context = PredictionContext(
                    tr_id=row["tr_id"], target_stop_id=row["target_stop_id"],
                    current_time=at, target_time_begin=target.time_begin,
                    cur_dev_s=float(row["cur_dev_s"]),
                )
                prediction = await predictor.predict(context)
                incident = incidents.process(
                    context=context,
                    predicted_delay_s=float(prediction["predicted_delay_s"]),
                    current_deviation_source="validate-point",
                    delay_probability=prediction.get("delay_probability"),
                    reason_factors=prediction.get("reason_factors"),
                )
                record = dashboard.build_record(incident).model_dump()
                # Validate IDs encode UTC epoch seconds although T is a naive
                # Moscow wall-clock timestamp; preserve the supplied identity.
                record["sampleId"] = row["sample_id"]
                self._records.append(record)
                self.completed += 1
                await asyncio.sleep(0)
            self.state = "complete"
        except Exception as error:
            self.error = str(error)
            self.state = "failed"
            LOG.exception("Historical replay failed")
