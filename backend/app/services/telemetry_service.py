from app.models.telemetry import TelemetryPoint
from app.services.vehicle_state_service import VehicleStateService


class TelemetryService:
    def __init__(
        self,
        vehicle_state_service: VehicleStateService,
    ) -> None:
        self._vehicle_state_service = vehicle_state_service

    def process(self, telemetry: TelemetryPoint) -> None:
        self._vehicle_state_service.add(telemetry)