from datetime import datetime

from pydantic import BaseModel


class SchedulePoint(BaseModel):
    tr_id: str
    stop_id: str

    time_begin: datetime

    longitude: float | None = None
    latitude: float | None = None
    address: str | None = None


class PredictionContext(BaseModel):
    tr_id: str
    target_stop_id: str

    current_time: datetime
    target_time_begin: datetime

    cur_dev_s: float


class CurrentDeviation(BaseModel):
    tr_id: str
    cur_dev_s: float


class ObservedArrival(BaseModel):
    tr_id: str
    stop_id: str
    actual_time: datetime
