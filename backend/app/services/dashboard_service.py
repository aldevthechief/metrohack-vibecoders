from zoneinfo import ZoneInfo
from datetime import timedelta

from app.models.dashboard import DashboardRecord, DashboardResponse
from app.models.incident import Incident
from app.services.schedule_service import ScheduleService
from app.services.vehicle_state_service import VehicleStateService


class DashboardService:
    def __init__(
        self,
        vehicle_state_service: VehicleStateService,
        schedule_service: ScheduleService,
    ) -> None:
        self._vehicle_state_service = vehicle_state_service
        self._schedule_service = schedule_service
        self._records: list[DashboardRecord] = []

    def record_incident(self, incident: Incident) -> None:
        self._records.append(self.build_record(incident))
        self._records = self._records[-500:]

    def get_records(self) -> list[DashboardRecord]:
        return list(self._records)

    def build_record(
        self,
        incident: Incident,
    ) -> DashboardRecord:
        target = self._schedule_service.get_target(
            tr_id=incident.tr_id,
            target_stop_id=incident.target_stop_id,
        )

        if target is None:
            raise ValueError(
                f"Target stop '{incident.target_stop_id}' "
                f"not found for trip '{incident.tr_id}'"
            )

        history = self._vehicle_state_service.get_history(
            tr_id=incident.tr_id,
            until=incident.current_time,
        )

        valid_positions = [
            point for point in history
            if point.location_valid is True
            and point.longitude is not None
            and point.latitude is not None
        ]
        last_position = valid_positions[-1] if valid_positions else None

        position = None

        if (
            last_position is not None
        ):
            position = [
                last_position.longitude,
                last_position.latitude,
            ]

        target_coordinate = None

        if (
            target.longitude is not None
            and target.latitude is not None
        ):
            target_coordinate = [
                target.longitude,
                target.latitude,
            ]

        trail = [
            [point.longitude, point.latitude]
            for point in valid_positions
        ]

        route = self._build_route(
            tr_id=incident.tr_id,
        )

        telemetry_time = (
            last_position.event_time.isoformat(sep=" ")
            if last_position is not None
            else None
        )

        telemetry_age = (
            (incident.current_time - last_position.event_time).total_seconds()
            if last_position is not None
            else None
        )

        horizon = (
            target.time_begin - incident.current_time
        ).total_seconds()

        sample_time = incident.current_time
        if sample_time.tzinfo is None:
            sample_time = sample_time.replace(tzinfo=ZoneInfo("Europe/Moscow"))

        sample_id = (
            f"{incident.tr_id}_"
            f"{int(sample_time.timestamp())}"
        )

        return DashboardRecord(
            sampleId=sample_id,
            vehicleId=incident.tr_id,

            timestamp=incident.current_time.isoformat(sep=" "),
            targetTime=target.time_begin.isoformat(sep=" "),

            targetStopId=incident.target_stop_id,
            targetAddress=target.address or f"Остановка № {target.stop_id}",
            segmentLabel=self._segment_label(incident.tr_id, target.stop_id),

            targetCoordinate=target_coordinate,
            position=position,

            telemetryTime=telemetry_time,
            telemetryAgeSec=telemetry_age,

            speedKmh=incident.speed_kmh,
            meanSpeedKmh=incident.mean_speed_kmh,
            stopFraction=incident.stop_fraction,

            currentDeviationSec=incident.current_deviation_s,
            currentDeviationSource=incident.current_deviation_source,
            predictionSec=incident.predicted_delay_s,
            delayProbability=incident.delay_probability,
            estimatedArrival=(target.time_begin + timedelta(seconds=incident.predicted_delay_s)).isoformat(sep=" "),
            reasonFactors=incident.reason_factors,
            horizonSec=horizon,

            signal=incident.signal,
            riskLevel=incident.risk_level.value,

            route=route,
            trail=trail,
        )

    def build_response(
        self,
        records: list[DashboardRecord],
    ) -> DashboardResponse:
        if records:
            date = records[-1].timestamp[:10]
        else:
            date = ""

        return DashboardResponse(
            source="backend-live",
            date=date,
            records=records,
        )

    def _build_route(
        self,
        tr_id: str,
    ) -> list[list[float]]:
        schedule = self._schedule_service.get_trip_schedule(
            tr_id=tr_id,
        )

        return [
            [point.longitude, point.latitude]
            for point in schedule
            if point.longitude is not None
            and point.latitude is not None
        ]

    def _segment_label(self, tr_id: str, target_stop_id: str) -> str:
        schedule = self._schedule_service.get_trip_schedule(tr_id)
        for index, stop in enumerate(schedule):
            if stop.stop_id == target_stop_id:
                previous = next((item for item in reversed(schedule[:index]) if item.address), None)
                if previous and stop.address:
                    return f"{previous.address} → {stop.address}"
                break
        return f"До остановки № {target_stop_id}"
