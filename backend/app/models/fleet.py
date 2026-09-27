from pydantic import BaseModel, Field


class FleetVehicle(BaseModel):
    vehicleId: str
    unitId: str | None = None
    source: str = "ndtp"
    position: list[float] | None = None
    trail: list[list[float]] = Field(default_factory=list)
    telemetryTime: str | None = None
    lastReceivedAt: str
    telemetryAgeSec: float | None = None
    speedKmh: float | None = None
    headingDeg: float | None = None
    packetCount15m: int = 0
    meanSpeed5mKmh: float | None = None
    stoppedFraction5m: float | None = None
    status: str
    predictionStatus: str


class FleetResponse(BaseModel):
    source: str = "live-telemetry"
    generatedAt: str
    vehicles: list[FleetVehicle]
