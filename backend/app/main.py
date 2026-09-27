import httpx
import json
import os
import logging
from csv import DictReader
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.models.dashboard import DashboardResponse
from app.models.incident import Incident
from app.models.schedule import CurrentDeviation, ObservedArrival, PredictionContext, SchedulePoint
from app.models.telemetry import NdtpUnitMapping, TelemetryPoint

from app.services.dashboard_service import DashboardService
from app.services.incident_service import IncidentService
from app.services.ndtp_service import NdtpServer
from app.services.prediction_context_service import PredictionContextService
from app.services.prediction_service import PredictionService
from app.services.processing_service import ProcessingService
from app.services.schedule_service import ScheduleService
from app.services.stop_arrival_service import StopArrivalService
from app.services.telemetry_service import TelemetryService
from app.services.vehicle_state_service import VehicleStateService

from app.services.features.feature_service import FeatureService
from app.services.features.schedule_features import ScheduleFeatureService
from app.services.features.spatial_features import SpatialFeatureService
from app.services.features.telemetry_features import TelemetryFeatureService


@asynccontextmanager
async def lifespan(_: FastAPI):
    schedule_path = os.getenv("SCHEDULE_PLAN_PATH")
    if schedule_path is None:
        local_plan = Path(__file__).resolve().parents[2] / "dataset" / "validate" / "schedule_plan.csv"
        schedule_path = str(local_plan) if local_plan.is_file() else None
    if schedule_path:
        loaded = schedule_service.load_plan_csv(Path(schedule_path))
        logging.getLogger(__name__).info("Loaded %s planned stops from %s", loaded, schedule_path)

    units_path = os.getenv("NDTP_UNITS_PATH")
    if units_path is None:
        local_units = Path(__file__).resolve().parents[1] / "config" / "ndtp_units.csv"
        units_path = str(local_units) if local_units.is_file() else None
    if units_path:
        with Path(units_path).open(encoding="utf-8", newline="") as stream:
            for row in DictReader(stream):
                mapping = NdtpUnitMapping.model_validate({
                    "unit_id": row["unit_id"], "tr_id": row["tr_id"]
                })
                ndtp_server.register_unit(mapping.unit_id, mapping.tr_id)
                deviation = (row.get("cur_dev_s") or "").strip()
                if deviation:
                    prediction_context_service.set_current_deviation(
                        mapping.tr_id, float(deviation), source="configured"
                    )

    await ndtp_server.start()
    try:
        yield
    finally:
        await ndtp_server.close()


app = FastAPI(
    title="Transport Delay Predictor Backend",
    description="Backend API for transport delay prediction",
    version="0.4.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

vehicle_state_service = VehicleStateService()

telemetry_service = TelemetryService(
    vehicle_state_service=vehicle_state_service,
)

schedule_service = ScheduleService()

telemetry_feature_service = TelemetryFeatureService(
    vehicle_state_service=vehicle_state_service,
)

schedule_feature_service = ScheduleFeatureService(
    schedule_service=schedule_service,
)

spatial_feature_service = SpatialFeatureService(
    vehicle_state_service=vehicle_state_service,
)

feature_service = FeatureService(
    schedule_feature_service=schedule_feature_service,
    spatial_feature_service=spatial_feature_service,
    telemetry_feature_service=telemetry_feature_service,
    schedule_service=schedule_service,
)

prediction_service = PredictionService(
    feature_service=feature_service,
    ml_service_url="http://127.0.0.1:8001",
)

incident_service = IncidentService(
    feature_service=feature_service,
)

dashboard_service = DashboardService(
    vehicle_state_service=vehicle_state_service,
    schedule_service=schedule_service,
)

prediction_context_service = PredictionContextService()

stop_arrival_service = StopArrivalService(
    vehicle_state_service=vehicle_state_service,
    schedule_service=schedule_service,
    prediction_context_service=prediction_context_service,
)

processing_service = ProcessingService(
    telemetry_service=telemetry_service,
    prediction_context_service=prediction_context_service,
    prediction_service=prediction_service,
    incident_service=incident_service,
    dashboard_service=dashboard_service,
    schedule_service=schedule_service,
    stop_arrival_service=stop_arrival_service,
)

ndtp_server = NdtpServer(
    processing_service=processing_service,
    host=os.getenv("NDTP_HOST", "0.0.0.0"),
    port=int(os.getenv("NDTP_PORT", "9201")),
)


# ============================================================
# Health
# ============================================================

@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


# ============================================================
# Telemetry
# ============================================================

@app.post("/api/v1/telemetry")
async def add_telemetry(
        telemetry: TelemetryPoint,
) -> dict:
    try:
        incident = await processing_service.process_telemetry(
            telemetry=telemetry,
        )

        return {
            "status": "ok",
            "prediction_updated": incident is not None,
        }

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    except httpx.HTTPError as error:
        raise HTTPException(
            status_code=503,
            detail="ML service unavailable",
        ) from error


@app.post("/api/v1/ndtp/units")
async def register_ndtp_unit(mapping: NdtpUnitMapping) -> dict[str, str]:
    ndtp_server.register_unit(mapping.unit_id, mapping.tr_id)
    return {
        "status": "ok",
        "unit_id": str(mapping.unit_id),
        "tr_id": mapping.tr_id,
    }


@app.get("/api/v1/ndtp/status")
async def get_ndtp_status() -> dict:
    return ndtp_server.status()


@app.get("/api/v1/vehicles")
async def get_vehicles() -> list[str]:
    return vehicle_state_service.get_vehicle_ids()


@app.get("/api/v1/vehicles/{tr_id}/latest")
async def get_latest_telemetry(
        tr_id: str,
) -> TelemetryPoint:
    telemetry = vehicle_state_service.get_latest(tr_id)

    if telemetry is None:
        raise HTTPException(
            status_code=404,
            detail="Vehicle not found",
        )

    return telemetry


@app.get("/api/v1/vehicles/{tr_id}/history")
async def get_vehicle_history(
        tr_id: str,
) -> list[TelemetryPoint]:
    return vehicle_state_service.get_history(tr_id)


# ============================================================
# Schedule
# ============================================================

@app.post("/api/v1/schedule")
async def add_schedule_point(
        point: SchedulePoint,
) -> dict[str, str]:
    schedule_service.add(point)

    return {"status": "ok"}


@app.get("/api/v1/schedule/{tr_id}")
async def get_schedule(
        tr_id: str,
) -> list[SchedulePoint]:
    return schedule_service.get_trip_schedule(tr_id)


# ============================================================
# Prediction Context
# ============================================================

@app.post("/api/v1/current-deviation")
async def set_current_deviation(deviation: CurrentDeviation) -> dict[str, str]:
    prediction_context_service.set_current_deviation(
        deviation.tr_id, deviation.cur_dev_s, source="provided"
    )
    return {"status": "ok", "tr_id": deviation.tr_id}


@app.post("/api/v1/arrivals")
async def record_arrival(arrival: ObservedArrival) -> dict[str, str | float]:
    planned = schedule_service.get_target(arrival.tr_id, arrival.stop_id)
    if planned is None:
        raise HTTPException(status_code=404, detail="Planned stop not found")
    deviation = (arrival.actual_time - planned.time_begin).total_seconds()
    prediction_context_service.set_current_deviation(
        arrival.tr_id, deviation, source="arrival-feed", observed_at=arrival.actual_time
    )
    return {"status": "ok", "tr_id": arrival.tr_id, "cur_dev_s": deviation}


@app.post("/api/v1/prediction-context")
async def set_prediction_context(
        context: PredictionContext,
) -> dict[str, str]:
    target = schedule_service.get_target(
        tr_id=context.tr_id,
        target_stop_id=context.target_stop_id,
    )

    if target is None:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Target stop '{context.target_stop_id}' "
                f"not found for trip '{context.tr_id}'"
            ),
        )

    prediction_context_service.set(context)

    return {
        "status": "ok",
        "tr_id": context.tr_id,
    }


# ============================================================
# Features
# ============================================================

@app.get("/api/v1/vehicles/{tr_id}/features")
async def get_telemetry_features(
        tr_id: str,
        at: str,
) -> dict:
    from datetime import datetime

    try:
        timestamp = datetime.fromisoformat(at)

        return telemetry_feature_service.build(
            tr_id=tr_id,
            at=timestamp,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error


@app.post("/api/v1/features/schedule")
async def get_schedule_features(
        context: PredictionContext,
) -> dict:
    return schedule_feature_service.build(
        context=context,
    )


@app.get("/api/v1/vehicles/{tr_id}/spatial-features")
async def get_spatial_features(
        tr_id: str,
        at: str,
        target_longitude: float,
        target_latitude: float,
) -> dict:
    from datetime import datetime

    try:
        timestamp = datetime.fromisoformat(at)

        return spatial_feature_service.build(
            tr_id=tr_id,
            at=timestamp,
            target_longitude=target_longitude,
            target_latitude=target_latitude,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error


@app.post("/api/v1/features")
async def get_features(
        context: PredictionContext,
) -> dict:
    try:
        return feature_service.build(
            context=context,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error


@app.post("/api/v1/predict")
async def predict(
        context: PredictionContext,
) -> dict:
    try:
        return await prediction_service.predict(
            context=context,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    except httpx.HTTPError as error:
        raise HTTPException(
            status_code=503,
            detail="ML service unavailable",
        ) from error


@app.post(
    "/api/v1/incidents/evaluate",
    response_model=Incident,
)
async def evaluate_incident(
        context: PredictionContext,
) -> Incident:
    try:
        prediction = await prediction_service.predict(context=context)

        return incident_service.process(
            context=context,
            predicted_delay_s=float(prediction["predicted_delay_s"]),
            delay_probability=prediction.get("delay_probability"),
            reason_factors=prediction.get("reason_factors"),
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    except httpx.HTTPError as error:
        raise HTTPException(
            status_code=503,
            detail="ML service unavailable",
        ) from error


@app.get(
    "/api/v1/incidents",
    response_model=list[Incident],
)
async def get_incidents() -> list[Incident]:
    return incident_service.get_all()


@app.get(
    "/api/v1/incidents/{tr_id}",
    response_model=Incident,
)
async def get_vehicle_incident(
        tr_id: str,
) -> Incident:
    incident = incident_service.get_by_vehicle(tr_id)

    if incident is None:
        raise HTTPException(
            status_code=404,
            detail="Incident not found",
        )

    return incident

@app.get(
    "/api/dashboard",
    response_model=DashboardResponse,
)
async def get_dashboard() -> DashboardResponse:
    records = dashboard_service.get_records()
    if records:
        return dashboard_service.build_response(records=records)

    default_replay_path = (
        Path(__file__).resolve().parents[2] / "frontend" / "src" / "data" / "demo.json"
    )
    replay_path = Path(os.getenv("DASHBOARD_REPLAY_PATH", str(default_replay_path)))
    if replay_path.is_file():
        with replay_path.open(encoding="utf-8") as stream:
            replay = json.load(stream)
        return DashboardResponse.model_validate({
            "source": "submission-replay",
            "date": replay.get("date", ""),
            "records": replay["records"],
        })

    return dashboard_service.build_response(records=[])
