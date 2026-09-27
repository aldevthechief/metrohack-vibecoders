from app.models.incident import Incident, RiskLevel
from app.models.schedule import PredictionContext
from app.services.features.feature_service import FeatureService


class IncidentService:
    MEDIUM_DELAY_S = 60.0
    HIGH_DELAY_S = 120.0

    CURRENT_DEVIATION_SIGNAL_S = 120.0

    LONG_STOP_FRACTION = 0.7
    LOW_MEAN_SPEED_KMH = 10.0

    def __init__(self, feature_service: FeatureService) -> None:
        self._feature_service = feature_service
        self._incidents: dict[str, Incident] = {}

    def process(
        self,
        context: PredictionContext,
        predicted_delay_s: float,
        current_deviation_source: str | None = None,
        delay_probability: float | None = None,
        reason_factors: list[dict] | None = None,
    ) -> Incident:
        features = self._feature_service.build(context=context)

        speed = self._to_float(features.get("speed_now"))
        mean_speed = self._to_float(features.get("speed_mean_5m"))
        stop_fraction = self._to_float(features.get("stopped_fraction_5m"))

        risk_level = self._calculate_risk(
            predicted_delay_s=predicted_delay_s,
        )

        signal = self._detect_signal(
            current_deviation_s=context.cur_dev_s,
            mean_speed_kmh=mean_speed,
            stop_fraction=stop_fraction,
        )

        incident = Incident(
            tr_id=context.tr_id,
            target_stop_id=context.target_stop_id,
            current_time=context.current_time,
            current_deviation_s=context.cur_dev_s,
            current_deviation_source=current_deviation_source,
            predicted_delay_s=predicted_delay_s,
            delay_probability=delay_probability,
            reason_factors=reason_factors or [],
            risk_level=risk_level,
            signal=signal,
            speed_kmh=speed,
            mean_speed_kmh=mean_speed,
            stop_fraction=stop_fraction,
        )

        self._incidents[context.tr_id] = incident

        return incident

    def get_all(self) -> list[Incident]:
        return list(self._incidents.values())

    def get_by_vehicle(self, tr_id: str) -> Incident | None:
        return self._incidents.get(tr_id)

    def _calculate_risk(
        self,
        predicted_delay_s: float,
    ) -> RiskLevel:
        if predicted_delay_s > self.HIGH_DELAY_S:
            return RiskLevel.HIGH

        if predicted_delay_s >= self.MEDIUM_DELAY_S:
            return RiskLevel.MEDIUM

        return RiskLevel.LOW

    def _detect_signal(
        self,
        current_deviation_s: float,
        mean_speed_kmh: float | None,
        stop_fraction: float | None,
    ) -> str:
        if current_deviation_s >= self.CURRENT_DEVIATION_SIGNAL_S:
            return "Уже есть отклонение"

        if (
            stop_fraction is not None
            and stop_fraction >= self.LONG_STOP_FRACTION
        ):
            return "Длительный простой"

        if (
            mean_speed_kmh is not None
            and mean_speed_kmh <= self.LOW_MEAN_SPEED_KMH
        ):
            return "Низкая скорость"

        return "Явного сигнала нет"

    @staticmethod
    def _to_float(value: object) -> float | None:
        if value is None:
            return None

        return float(value)
