from datetime import datetime

from app.models.schedule import PredictionContext
from app.services.features.schedule_features import ScheduleFeatureService
from app.services.features.spatial_features import SpatialFeatureService
from app.services.features.telemetry_features import TelemetryFeatureService
from app.services.schedule_service import ScheduleService


class FeatureService:
    def __init__(
        self,
        schedule_feature_service: ScheduleFeatureService,
        spatial_feature_service: SpatialFeatureService,
        telemetry_feature_service: TelemetryFeatureService,
        schedule_service: ScheduleService,
    ) -> None:
        self._schedule_feature_service = schedule_feature_service
        self._spatial_feature_service = spatial_feature_service
        self._telemetry_feature_service = telemetry_feature_service
        self._schedule_service = schedule_service

    def build(
        self,
        context: PredictionContext,
    ) -> dict[str, float | int | str | None]:
        target = self._schedule_service.get_target(
            tr_id=context.tr_id,
            target_stop_id=context.target_stop_id,
        )

        if target is None:
            raise ValueError(
                f"Target stop '{context.target_stop_id}' "
                f"not found for trip '{context.tr_id}'"
            )

        if target.time_begin != context.target_time_begin:
            raise ValueError("Target time does not match the registered schedule")

        horizon_s = (target.time_begin - context.current_time).total_seconds()
        if not 600 < horizon_s <= 900:
            raise ValueError("Prediction horizon must be in (10, 15] minutes")

        if (
            target.longitude is None
            or target.latitude is None
        ):
            raise ValueError(
                "Target stop has no coordinates"
            )

        schedule_features = (
            self._schedule_feature_service.build(
                context=context,
            )
        )

        telemetry_features = (
            self._telemetry_feature_service.build(
                tr_id=context.tr_id,
                at=context.current_time,
            )
        )

        spatial_features = (
            self._spatial_feature_service.build(
                tr_id=context.tr_id,
                at=context.current_time,
                target_longitude=target.longitude,
                target_latitude=target.latitude,
            )
        )

        return {
            **schedule_features,
            **spatial_features,
            **telemetry_features,
        }
