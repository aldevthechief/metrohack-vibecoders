"""Estimate a stop arrival from sustained slow GPS fixes near a planned stop."""

import math
from datetime import datetime

from app.models.telemetry import TelemetryPoint
from app.services.prediction_context_service import PredictionContextService
from app.services.schedule_service import ScheduleService
from app.services.vehicle_state_service import VehicleStateService


class StopArrivalService:
    RADIUS_M = 35.0
    MAX_SPEED_KMH = 5.0
    MIN_DWELL_S = 10.0
    MAX_FIX_SPAN_S = 60.0
    MAX_SCHEDULE_OFFSET_S = 20 * 60

    def __init__(
        self,
        vehicle_state_service: VehicleStateService,
        schedule_service: ScheduleService,
        prediction_context_service: PredictionContextService,
    ) -> None:
        self._vehicle_state_service = vehicle_state_service
        self._schedule_service = schedule_service
        self._prediction_context_service = prediction_context_service
        self._confirmed_stops: dict[str, set[str]] = {}
        self._last_planned_time: dict[str, datetime] = {}

    def observe(self, telemetry: TelemetryPoint) -> float | None:
        history = self._vehicle_state_service.get_history(
            telemetry.tr_id, until=max(telemetry.event_time, telemetry.receive_time)
        )
        if len(history) < 3 or history[-1] is not telemetry:
            return None
        fixes = history[-3:]
        times = [point.event_time for point in fixes]
        if not (times[0] < times[1] < times[2]):
            return None
        span = (times[2] - times[0]).total_seconds()
        if not self.MIN_DWELL_S <= span <= self.MAX_FIX_SPAN_S:
            return None
        if any(not self._valid_slow_fix(point) for point in fixes):
            return None

        candidates = []
        confirmed = self._confirmed_stops.setdefault(telemetry.tr_id, set())
        last_planned = self._last_planned_time.get(telemetry.tr_id)
        for stop in self._schedule_service.get_trip_schedule(telemetry.tr_id):
            if stop.stop_id in confirmed or (last_planned and stop.time_begin <= last_planned):
                continue
            offset = abs((times[0] - stop.time_begin).total_seconds())
            if offset > self.MAX_SCHEDULE_OFFSET_S or stop.longitude is None or stop.latitude is None:
                continue
            distances = [
                self._distance_m(point.longitude, point.latitude, stop.longitude, stop.latitude)
                for point in fixes
            ]
            if max(distances) <= self.RADIUS_M:
                candidates.append((offset, max(distances), stop))
        if not candidates:
            return None

        _, _, stop = min(candidates, key=lambda item: (item[0], item[1]))
        deviation = (times[0] - stop.time_begin).total_seconds()
        accepted = self._prediction_context_service.set_current_deviation(
            telemetry.tr_id, deviation, source="gps-estimate", observed_at=times[0]
        )
        if not accepted:
            return None
        confirmed.add(stop.stop_id)
        self._last_planned_time[telemetry.tr_id] = stop.time_begin
        return deviation

    def _valid_slow_fix(self, point: TelemetryPoint) -> bool:
        return (
            point.location_valid is True
            and point.longitude is not None
            and point.latitude is not None
            and point.speed is not None
            and 0 <= point.speed <= self.MAX_SPEED_KMH
        )

    @staticmethod
    def _distance_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
        latitude1, latitude2 = math.radians(lat1), math.radians(lat2)
        delta_lat = latitude2 - latitude1
        delta_lon = math.radians(lon2 - lon1)
        value = (
            math.sin(delta_lat / 2) ** 2
            + math.cos(latitude1) * math.cos(latitude2) * math.sin(delta_lon / 2) ** 2
        )
        return 2 * 6_371_008.8 * math.asin(min(1.0, math.sqrt(value)))
