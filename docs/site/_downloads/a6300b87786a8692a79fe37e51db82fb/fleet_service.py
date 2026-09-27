"""Current positions for every vehicle seen in the telemetry stream."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.models.fleet import FleetResponse, FleetVehicle
from app.services.dashboard_service import DashboardService
from app.services.prediction_context_service import PredictionContextService
from app.services.schedule_service import ScheduleService
from app.services.vehicle_state_service import VehicleStateService


class FleetService:
    ACTIVE_WINDOW = timedelta(minutes=15)
    FRESH_WINDOW = timedelta(minutes=2)

    def __init__(
        self,
        vehicle_state_service: VehicleStateService,
        schedule_service: ScheduleService,
        prediction_context_service: PredictionContextService,
        dashboard_service: DashboardService,
    ) -> None:
        self._vehicle_state_service = vehicle_state_service
        self._schedule_service = schedule_service
        self._prediction_context_service = prediction_context_service
        self._dashboard_service = dashboard_service
        self._emulator_unit_ids: set[str] = set()

    def set_emulator_unit_ids(self, unit_ids: set[str]) -> None:
        self._emulator_unit_ids = unit_ids

    def build_response(self, now: datetime | None = None) -> FleetResponse:
        now = now or datetime.now(ZoneInfo("Europe/Moscow")).replace(tzinfo=None)
        latest_predictions = {}
        for record in self._dashboard_service.get_records():
            latest_predictions[record.vehicleId] = record

        vehicles = []
        for tr_id in self._vehicle_state_service.get_vehicle_ids():
            history = self._vehicle_state_service.get_history(tr_id)
            if not history:
                continue
            last_received = max(point.receive_time for point in history)
            if now - last_received > self.ACTIVE_WINDOW:
                continue
            valid = [
                point for point in history
                if point.location_valid is True
                and point.longitude is not None
                and point.latitude is not None
            ]
            latest = valid[-1] if valid else None
            recent = [point for point in history if now - timedelta(minutes=5) <= point.event_time <= now and point.speed is not None]
            recent_speeds = [point.speed for point in recent]
            gps_age = (now - latest.event_time).total_seconds() if latest else None
            status = (
                "no-gps" if latest is None else
                "live" if gps_age is not None and gps_age <= self.FRESH_WINDOW.total_seconds()
                and now - last_received <= self.FRESH_WINDOW else "stale"
            )
            prediction = latest_predictions.get(tr_id)
            prediction_age = (
                (now - datetime.fromisoformat(prediction.timestamp)).total_seconds()
                if prediction else None
            )
            if prediction_age is not None and 0 <= prediction_age <= self.FRESH_WINDOW.total_seconds():
                prediction_status = "available"
            elif not self._schedule_service.get_trip_schedule(tr_id):
                prediction_status = "no-schedule"
            elif self._schedule_service.get_next_target(tr_id, now) is None:
                prediction_status = "outside-window"
            elif self._prediction_context_service.get_current_deviation(tr_id) is None:
                prediction_status = "no-deviation"
            else:
                prediction_status = "pending"
            vehicles.append(FleetVehicle(
                vehicleId=tr_id,
                unitId=history[-1].unit_id,
                source=(
                    "emulator" if history[-1].unit_id in self._emulator_unit_ids else
                    "ndtp" if history[-1].unit_id else "http"
                ),
                position=[latest.longitude, latest.latitude] if latest else None,
                trail=[[point.longitude, point.latitude] for point in valid[-60:]],
                telemetryTime=latest.event_time.isoformat(sep=" ") if latest else None,
                gpsReceivedAt=latest.receive_time.isoformat(sep=" ") if latest else None,
                lastReceivedAt=last_received.isoformat(sep=" "),
                telemetryAgeSec=max(0, gps_age) if gps_age is not None else None,
                speedKmh=latest.speed if latest else None,
                headingDeg=latest.heading if latest else None,
                packetCount15m=sum(now - self.ACTIVE_WINDOW <= point.receive_time <= now for point in history),
                meanSpeed5mKmh=sum(recent_speeds) / len(recent_speeds) if recent_speeds else None,
                stoppedFraction5m=sum(speed < 2 for speed in recent_speeds) / len(recent_speeds) if recent_speeds else None,
                status=status,
                predictionStatus=prediction_status,
            ))
        vehicles.sort(key=lambda item: item.vehicleId)
        return FleetResponse(generatedAt=now.isoformat(sep=" "), vehicles=vehicles)
