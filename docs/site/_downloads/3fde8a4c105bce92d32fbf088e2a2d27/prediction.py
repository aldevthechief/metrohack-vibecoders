from pydantic import BaseModel


class PredictionRequest(BaseModel):
    features: dict[str, float | int | str | None]


class PredictionResponse(BaseModel):
    predicted_delay_s: float
    delay_probability: float
    delay_threshold_sec: int
    probability_method: str
    reason_factors: list[dict]
