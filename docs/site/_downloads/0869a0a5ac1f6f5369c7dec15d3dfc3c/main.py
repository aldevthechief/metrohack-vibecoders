from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from .models.prediction import (
    PredictionRequest,
    PredictionResponse,
)
from .services.model_service import ModelService


app = FastAPI(
    title="Transport Delay Predictor ML Service",
    description="ML inference service for transport delay prediction",
    version="0.2.0",
)


model_service = ModelService()


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")


@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
    }


@app.post(
    "/predict",
    response_model=PredictionResponse,
)
async def predict(
    request: PredictionRequest,
) -> PredictionResponse:
    prediction = model_service.predict_details(
        features=request.features,
    )

    return PredictionResponse(**prediction)
