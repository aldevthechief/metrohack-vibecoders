import math

from app.models.schedule import PredictionContext
from app.services.schedule_service import ScheduleService


class ScheduleFeatureService:
    def __init__(
            self,
            schedule_service: ScheduleService,
    ) -> None:
        self._schedule_service = schedule_service

    def build(
            self,
            context: PredictionContext,
    ) -> dict[str, float | int | str]:
        now = context.current_time
        target_time = context.target_time_begin

        hour = now.hour
        minute = now.minute

        minute_of_day = (
                hour * 60
                + minute
        )

        day_of_week = now.weekday()

        is_weekend = int(
            day_of_week >= 5
        )

        sin_time = math.sin(
            2
            * math.pi
            * minute_of_day
            / 1440
        )

        cos_time = math.cos(
            2
            * math.pi
            * minute_of_day
            / 1440
        )

        target_hour = (
            target_time.hour
        )

        target_minute_of_day = (
                target_hour * 60
                + target_time.minute
        )

        forecast_horizon_s = (
                target_time - now
        ).total_seconds()

        cur_dev_s = (
            context.cur_dev_s
        )

        abs_cur_dev = abs(
            cur_dev_s
        )

        is_late_now = int(
            cur_dev_s > 0
        )

        is_early_now = int(
            cur_dev_s < 0
        )

        stops_to_target = (
            self._calculate_stops_to_target(
                context=context,
            )
        )

        return {
            "tr_id": context.tr_id,
            "target_stop_id": (
                context.target_stop_id
            ),

            "hour": hour,
            "minute": minute,
            "minute_of_day": minute_of_day,

            "day_of_week": day_of_week,
            "is_weekend": is_weekend,

            "sin_time": sin_time,
            "cos_time": cos_time,

            "target_hour": target_hour,
            "target_minute_of_day": (
                target_minute_of_day
            ),

            "forecast_horizon_s": (
                forecast_horizon_s
            ),

            "cur_dev_s": cur_dev_s,
            "abs_cur_dev": abs_cur_dev,

            "is_late_now": is_late_now,
            "is_early_now": is_early_now,

            "stops_to_target": (
                stops_to_target
            ),
        }

    def _calculate_stops_to_target(
            self,
            context: PredictionContext,
    ) -> int:
        schedule = (
            self._schedule_service
            .get_trip_schedule(
                context.tr_id
            )
        )

        stops = {
            point.stop_id
            for point in schedule
            if (
                    point.time_begin
                    > context.current_time
                    and point.time_begin
                    <= context.target_time_begin
            )
        }

        return len(stops)
