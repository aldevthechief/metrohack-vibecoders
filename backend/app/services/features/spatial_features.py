import math
from datetime import datetime, timedelta

from app.services.vehicle_state_service import VehicleStateService


class SpatialFeatureService:
    EARTH_RADIUS_M = 6_371_008.8

    def __init__(
        self,
        vehicle_state_service: VehicleStateService,
    ) -> None:
        self._vehicle_state_service = vehicle_state_service

    def build(
        self,
        tr_id: str,
        at: datetime,
        target_longitude: float,
        target_latitude: float,
    ) -> dict[str, float | int | None]:
        history = self._vehicle_state_service.get_history(
            tr_id=tr_id,
            until=at,
        )

        result: dict[str, float | int | None] = {
            "sp_has_position": 0,
        }

        valid = [
            point
            for point in history
            if self._has_valid_position(point)
        ]

        if not valid:
            return result

        # Аналог:
        # drop_duplicates("event_time", keep="last")
        unique_by_time = {}

        for point in valid:
            unique_by_time[point.event_time] = point

        valid = sorted(
            unique_by_time.values(),
            key=lambda point: point.event_time,
        )

        current = valid[-1]

        position_age = (
            at - current.event_time
        ).total_seconds()

        distance = self._haversine_m(
            lon1=current.longitude,
            lat1=current.latitude,
            lon2=target_longitude,
            lat2=target_latitude,
        )

        result["sp_has_position"] = 1
        result["sp_position_age_s"] = position_age
        result["sp_distance_to_target_m"] = distance

        for minutes in (1, 3):
            query_time = at - timedelta(
                minutes=minutes,
            )

            previous = [
                point
                for point in valid
                if point.event_time <= query_time
            ]

            if not previous or position_age > 60:
                continue

            past = previous[-1]

            # В unified старая позиция допускается
            # максимум на 60 секунд раньше query_time.
            if (
                query_time - past.event_time
            ).total_seconds() > 60:
                continue

            elapsed = (
                current.event_time
                - past.event_time
            ).total_seconds()

            if elapsed <= 0:
                continue

            old_distance = self._haversine_m(
                lon1=past.longitude,
                lat1=past.latitude,
                lon2=target_longitude,
                lat2=target_latitude,
            )

            approach = (
                old_distance - distance
            )

            result[
                f"sp_approach_{minutes}m_m"
            ] = approach

            result[
                f"sp_approach_speed_{minutes}m_mps"
            ] = approach / elapsed

        return result

    @staticmethod
    def _has_valid_position(
        point,
    ) -> bool:
        if point.location_valid is not True:
            return False

        if (
            point.longitude is None
            or point.latitude is None
        ):
            return False

        if not -180 <= point.longitude <= 180:
            return False

        if not -90 <= point.latitude <= 90:
            return False

        if (
            point.longitude == 0
            and point.latitude == 0
        ):
            return False

        return True

    @classmethod
    def _haversine_m(
        cls,
        lon1: float,
        lat1: float,
        lon2: float,
        lat2: float,
    ) -> float:
        lon1_rad = math.radians(lon1)
        lat1_rad = math.radians(lat1)

        lon2_rad = math.radians(lon2)
        lat2_rad = math.radians(lat2)

        delta_lon = lon2_rad - lon1_rad
        delta_lat = lat2_rad - lat1_rad

        value = (
            math.sin(delta_lat / 2) ** 2
            + math.cos(lat1_rad)
            * math.cos(lat2_rad)
            * math.sin(delta_lon / 2) ** 2
        )

        value = min(
            1.0,
            max(0.0, value),
        )

        return (
            2
            * cls.EARTH_RADIUS_M
            * math.asin(math.sqrt(value))
        )