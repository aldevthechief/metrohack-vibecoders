from datetime import datetime

from pydantic import BaseModel, Field


class TelemetryPoint(BaseModel):
    packet_id: str | None = None

    tr_id: str
    unit_id: str | None = None

    event_time: datetime
    gps_time: datetime | None = None
    receive_time: datetime

    speed: float | None = None
    heading: float | None = None
    altitude: float | None = None

    location_valid: bool | None = None

    longitude: float | None = None
    latitude: float | None = None

    is_hist: bool = False


class NdtpUnitMapping(BaseModel):
    unit_id: int = Field(ge=0, le=2_147_483_647)
    tr_id: str = Field(min_length=1)
