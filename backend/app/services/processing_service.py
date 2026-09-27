from app.models.incident import Incident
from app.models.schedule import PredictionContext
from app.models.telemetry import TelemetryPoint
from app.services.incident_service import IncidentService
from app.services.dashboard_service import DashboardService
from app.services.prediction_context_service import PredictionContextService
from app.services.prediction_service import PredictionService
from app.services.schedule_service import ScheduleService
from app.services.stop_arrival_service import StopArrivalService
from app.services.telemetry_service import TelemetryService


class ProcessingService:
    def __init__(
        self,
        telemetry_service: TelemetryService,
        prediction_context_service: PredictionContextService,
        prediction_service: PredictionService,
        incident_service: IncidentService,
        dashboard_service: DashboardService,
        schedule_service: ScheduleService,
        stop_arrival_service: StopArrivalService,
    ) -> None:
        self._telemetry_service = telemetry_service
        self._prediction_context_service = prediction_context_service
        self._prediction_service = prediction_service
        self._incident_service = incident_service
        self._dashboard_service = dashboard_service
        self._schedule_service = schedule_service
        self._stop_arrival_service = stop_arrival_service

    async def process_telemetry(
        self,
        telemetry: TelemetryPoint,
    ) -> Incident | None:
        self._telemetry_service.process(telemetry)
        self._stop_arrival_service.observe(telemetry)

        # A packet is available only when received; use that moment for the forecast.
        prediction_time = max(telemetry.event_time, telemetry.receive_time)
        target = self._schedule_service.get_next_target(telemetry.tr_id, prediction_time)
        cur_dev_s = self._prediction_context_service.get_current_deviation(telemetry.tr_id)
        deviation_source = self._prediction_context_service.get_current_deviation_source(telemetry.tr_id)
        if target is None or cur_dev_s is None:
            return None

        updated_context = PredictionContext(
            tr_id=telemetry.tr_id,
            target_stop_id=target.stop_id,
            current_time=prediction_time,
            target_time_begin=target.time_begin,
            cur_dev_s=cur_dev_s,
        )

        self._prediction_context_service.update_context(
            updated_context
        )

        prediction = await self._prediction_service.predict(context=updated_context)

        incident = self._incident_service.process(
            context=updated_context,
            predicted_delay_s=float(prediction["predicted_delay_s"]),
            current_deviation_source=deviation_source,
            delay_probability=prediction.get("delay_probability"),
            reason_factors=prediction.get("reason_factors"),
        )
        self._dashboard_service.record_incident(incident)
        return incident
