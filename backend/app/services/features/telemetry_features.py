from datetime import datetime, timedelta

from app.models.telemetry import TelemetryPoint
from app.services.vehicle_state_service import VehicleStateService


class TelemetryFeatureService:
    STOP_SPEED_KMH = 2.0

    WINDOWS = {
        "30s": 30,
        "1m": 60,
        "3m": 180,
        "5m": 300,
        "10m": 600,
        "15m": 900,
    }

    def __init__(
        self,
        vehicle_state_service: VehicleStateService,
    ) -> None:
        self._vehicle_state_service = vehicle_state_service

    def build(
        self,
        tr_id: str,
        at: datetime,
    ) -> dict[str, float | int | str | None]:
        history = self._vehicle_state_service.get_history(
            tr_id=tr_id,
            until=at,
        )

        if not history:
            return {
                "packet_count_15m": 0,
                "packet_frequency": 0.0,
            }

        result: dict[str, float | int | str | None] = {}

        last = history[-1]

        recent = [
            point
            for point in history
            if point.event_time > at - timedelta(minutes=15)
        ]

        speed_history = [
            point
            for point in history
            if point.speed is not None
        ]

        # -------------------------
        # Current values
        # -------------------------

        result["unit_id"] = (
            last.unit_id
            if last.unit_id is not None
            else "missing"
        )

        result["event_time"] = last.event_time.timestamp()

        result["gps_time"] = (
            last.gps_time.timestamp()
            if last.gps_time is not None
            else None
        )

        result["receive_time"] = last.receive_time.timestamp()

        result["speed_now"] = (
            speed_history[-1].speed
            if speed_history
            else None
        )

        result["last_packet_is_hist"] = int(last.is_hist)

        # -------------------------
        # Freshness
        # -------------------------

        result["telemetry_age"] = (
            at - last.event_time
        ).total_seconds()

        known_gps = [
            point.gps_time
            for point in history
            if point.gps_time is not None
        ]

        result["gps_age"] = (
            (at - known_gps[-1]).total_seconds()
            if known_gps
            else None
        )

        result["receive_delay"] = (
            last.receive_time - last.event_time
        ).total_seconds()

        # -------------------------
        # Packet quality
        # -------------------------

        result["packet_count_15m"] = len(recent)

        result["packet_frequency"] = (
            len(recent) / 15.0
        )

        result["hist_packet_fraction"] = (
            sum(
                int(point.is_hist)
                for point in recent
            ) / len(recent)
            if recent
            else None
        )

        result["mean_receive_delay"] = (
            sum(
                (
                    point.receive_time
                    - point.event_time
                ).total_seconds()
                for point in recent
            ) / len(recent)
            if recent
            else None
        )

        result["max_packet_gap"] = self._max_packet_gap(
            recent
        )

        # -------------------------
        # Rolling speed features
        # -------------------------

        for suffix, seconds in self.WINDOWS.items():
            window = [
                point
                for point in recent
                if point.event_time
                > at - timedelta(seconds=seconds)
            ]

            valid = [
                point
                for point in window
                if point.speed is not None
            ]

            speeds = [
                point.speed
                for point in valid
            ]

            self._add_speed_statistics(
                result=result,
                speeds=speeds,
                suffix=suffix,
            )

            if suffix in ("1m", "3m", "5m"):
                result[f"stopped_fraction_{suffix}"] = (
                    sum(
                        speed <= self.STOP_SPEED_KMH
                        for speed in speeds
                    ) / len(speeds)
                    if speeds
                    else None
                )

                result[f"speed_slope_{suffix}"] = (
                    self._speed_slope(valid)
                )

            if suffix == "5m":
                result["longest_stop_5m"] = (
                    self._longest_stop(valid)
                )

            if suffix == "10m":
                result["stop_count_10m"] = (
                    self._stop_count(valid)
                )

        # -------------------------
        # Current stop state
        # -------------------------

        if speed_history:
            result["time_since_last_move"] = (
                self._time_since_last_move(
                    history=speed_history,
                    at=at,
                )
            )

            result["current_stop_duration"] = (
                self._current_stop_duration(
                    history=speed_history,
                    at=at,
                )
            )
        else:
            result["time_since_last_move"] = None
            result["current_stop_duration"] = None

        return result

    @staticmethod
    def _add_speed_statistics(
        result: dict[str, float | int | str | None],
        speeds: list[float],
        suffix: str,
    ) -> None:
        if not speeds:
            for stat in (
                "mean",
                "std",
                "min",
                "max",
                "median",
            ):
                result[f"speed_{stat}_{suffix}"] = None

            return

        count = len(speeds)
        average = sum(speeds) / count

        result[f"speed_mean_{suffix}"] = average

        if count >= 2:
            variance = (
                sum(
                    (speed - average) ** 2
                    for speed in speeds
                )
                / (count - 1)
            )

            result[f"speed_std_{suffix}"] = variance ** 0.5
        else:
            result[f"speed_std_{suffix}"] = None

        result[f"speed_min_{suffix}"] = min(speeds)
        result[f"speed_max_{suffix}"] = max(speeds)

        sorted_speeds = sorted(speeds)
        middle = count // 2

        if count % 2 == 1:
            median = sorted_speeds[middle]
        else:
            median = (
                sorted_speeds[middle - 1]
                + sorted_speeds[middle]
            ) / 2

        result[f"speed_median_{suffix}"] = median

    @staticmethod
    def _max_packet_gap(
        history: list[TelemetryPoint],
    ) -> float | None:
        if len(history) < 2:
            return None

        gaps = [
            (
                history[index].event_time
                - history[index - 1].event_time
            ).total_seconds()
            for index in range(1, len(history))
        ]

        return max(gaps)

    @staticmethod
    def _speed_slope(
        points: list[TelemetryPoint],
    ) -> float | None:
        if len(points) < 2:
            return None

        first = points[0]
        last = points[-1]

        span_minutes = (
            last.event_time - first.event_time
        ).total_seconds() / 60.0

        if span_minutes <= 0:
            return None

        return (
            last.speed - first.speed
        ) / span_minutes

    def _longest_stop(
        self,
        points: list[TelemetryPoint],
    ) -> float | None:
        if not points:
            return None

        longest = 0.0
        stop_start: datetime | None = None

        for point in points:
            if point.speed <= self.STOP_SPEED_KMH:
                if stop_start is None:
                    stop_start = point.event_time

                duration = (
                    point.event_time - stop_start
                ).total_seconds()

                longest = max(
                    longest,
                    duration,
                )
            else:
                stop_start = None

        return longest

    def _stop_count(
        self,
        points: list[TelemetryPoint],
    ) -> int:
        if not points:
            return 0

        count = 0
        was_stopped = False

        for point in points:
            is_stopped = (
                point.speed <= self.STOP_SPEED_KMH
            )

            if is_stopped and not was_stopped:
                count += 1

            was_stopped = is_stopped

        return count

    def _time_since_last_move(
        self,
        history: list[TelemetryPoint],
        at: datetime,
    ) -> float | None:
        moving = [
            point
            for point in history
            if point.speed > self.STOP_SPEED_KMH
        ]

        if not moving:
            return None

        return (
            at - moving[-1].event_time
        ).total_seconds()

    def _current_stop_duration(
        self,
        history: list[TelemetryPoint],
        at: datetime,
    ) -> float:
        if history[-1].speed > self.STOP_SPEED_KMH:
            return 0.0

        last_moving_index: int | None = None

        for index, point in enumerate(history):
            if point.speed > self.STOP_SPEED_KMH:
                last_moving_index = index

        if last_moving_index is None:
            first_stop_index = 0
        else:
            first_stop_index = last_moving_index + 1

        return (
            at - history[first_stop_index].event_time
        ).total_seconds()