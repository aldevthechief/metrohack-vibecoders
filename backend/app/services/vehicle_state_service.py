from collections import defaultdict
from datetime import datetime, timedelta

from app.models.telemetry import TelemetryPoint


class VehicleStateService:
    def __init__(self, history_minutes: int = 15) -> None:
        self._history: dict[str, list[TelemetryPoint]] = defaultdict(list)
        self._history_window = timedelta(minutes=history_minutes)

    def add(self, telemetry: TelemetryPoint) -> None:
        history = self._history[telemetry.tr_id]

        history.append(telemetry)
        history.sort(key=lambda point: point.event_time)

        self._cleanup(
            tr_id=telemetry.tr_id,
            current_time=telemetry.receive_time,
        )

    def get_history(
        self,
        tr_id: str,
        until: datetime | None = None,
    ) -> list[TelemetryPoint]:
        history = self._history.get(tr_id, [])

        if until is None:
            return list(history)

        return [
            point
            for point in history
            if point.event_time <= until
            and point.receive_time <= until
        ]

    def get_latest(self, tr_id: str, until: datetime | None = None) -> TelemetryPoint | None:
        history = self.get_history(tr_id, until=until)

        if not history:
            return None

        return history[-1]

    def get_vehicle_ids(self) -> list[str]:
        return list(self._history.keys())

    def _cleanup(
        self,
        tr_id: str,
        current_time: datetime,
    ) -> None:
        threshold = current_time - self._history_window

        self._history[tr_id] = [
            point
            for point in self._history[tr_id]
            if point.event_time >= threshold
        ]
