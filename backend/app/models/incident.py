from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Incident(BaseModel):
    tr_id: str
    target_stop_id: str

    current_time: datetime

    current_deviation_s: float
    current_deviation_source: str | None = None
    predicted_delay_s: float
    delay_probability: float | None = None
    reason_factors: list[dict] = Field(default_factory=list)

    risk_level: RiskLevel
    signal: str

    speed_kmh: float | None = None
    mean_speed_kmh: float | None = None
    stop_fraction: float | None = None
