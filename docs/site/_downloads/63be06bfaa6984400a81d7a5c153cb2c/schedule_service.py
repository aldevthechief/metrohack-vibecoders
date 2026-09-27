from collections import defaultdict
from csv import DictReader
from datetime import datetime, timedelta
from pathlib import Path
import re

from app.models.schedule import SchedulePoint


class ScheduleService:
    def __init__(self) -> None:
        self._schedule: dict[
            str,
            list[SchedulePoint],
        ] = defaultdict(list)

    def add(
        self,
        point: SchedulePoint,
    ) -> None:
        schedule = self._schedule[
            point.tr_id
        ]

        schedule[:] = [item for item in schedule if item.stop_id != point.stop_id]
        schedule.append(point)

        schedule.sort(
            key=lambda item: item.time_begin,
        )

    def add_many(
        self,
        points: list[SchedulePoint],
    ) -> None:
        for point in points:
            self.add(point)

    def load_plan_csv(self, path: Path) -> int:
        """Load planned stops; repeated loads replace the same stop IDs."""
        count = 0
        with path.open(encoding="utf-8", newline="") as stream:
            for row in DictReader(stream):
                geometry = re.fullmatch(
                    r"POINT\s*\(\s*([-+\d.eE]+)\s+([-+\d.eE]+)\s*\)",
                    (row.get("geom") or "").strip(),
                )
                if not geometry:
                    continue
                self.add(SchedulePoint(
                    tr_id=str(row["tr_id"]),
                    stop_id=str(row["tt_action_item_id"]),
                    time_begin=datetime.fromisoformat(row["time_begin"]),
                    longitude=float(geometry.group(1)),
                    latitude=float(geometry.group(2)),
                    address=row.get("building_address") or None,
                ))
                count += 1
        return count

    def get_trip_schedule(
        self,
        tr_id: str,
    ) -> list[SchedulePoint]:
        return list(
            self._schedule.get(
                tr_id,
                [],
            )
        )

    def get_target(
        self,
        tr_id: str,
        target_stop_id: str,
    ) -> SchedulePoint | None:
        schedule = self._schedule.get(
            tr_id,
            [],
        )

        for point in schedule:
            if point.stop_id == target_stop_id:
                return point

        return None

    def get_next_target(self, tr_id: str, at: datetime) -> SchedulePoint | None:
        window_start = at + timedelta(minutes=10)
        window_end = at + timedelta(minutes=15)
        for point in self._schedule.get(tr_id, []):
            if window_start < point.time_begin <= window_end:
                return point
        return None
