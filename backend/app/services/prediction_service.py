import httpx
import os

from app.models.schedule import PredictionContext
from app.services.features.feature_service import FeatureService


class PredictionService:
    def __init__(
        self,
        feature_service: FeatureService,
        ml_service_url: str,
    ) -> None:
        self._feature_service = feature_service
        self._ml_service_url = os.getenv("ML_SERVICE_URL", ml_service_url).rstrip("/")

    async def predict(
        self,
        context: PredictionContext,
    ) -> dict:
        features = self._feature_service.build(context=context)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._ml_service_url}/predict",
                json={"features": features},
                timeout=5.0,
            )

        response.raise_for_status()

        return response.json()

    async def predict_delay(
        self,
        context: PredictionContext,
    ) -> float:
        result = await self.predict(context=context)

        return float(result["predicted_delay_s"])
