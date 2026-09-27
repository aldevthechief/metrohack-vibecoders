backend.app.models.dashboard
============================

Модели ответа дашборда. DashboardRecord описывает прогнозную точку, маршрут, телеметрию и объяснения; DashboardResponse объединяет записи. Координаты имеют порядок [долгота, широта], времена для UI передаются строками.

:download:`Скачать исходный код <../../backend/app/models/dashboard.py>`

DashboardRecord
---------------

.. code-block:: python

   class DashboardRecord(BaseModel)

Поля и константы класса:

.. code-block:: python

   sampleId: str
   vehicleId: str
   timestamp: str
   targetTime: str
   targetStopId: str
   targetAddress: str | None = None
   segmentLabel: str | None = None
   targetCoordinate: list[float] | None = None
   position: list[float] | None = None
   telemetryTime: str | None = None
   telemetryAgeSec: float | None = None
   speedKmh: float | None = None
   meanSpeedKmh: float | None = None
   stopFraction: float | None = None
   currentDeviationSec: float
   currentDeviationSource: str | None = None
   predictionSec: float
   delayProbability: float | None = None
   estimatedArrival: str | None = None
   reasonFactors: list[dict] = Field(default_factory=list)
   horizonSec: float
   signal: str
   riskLevel: str | None = None
   route: list[list[float]]
   trail: list[list[float]]

DashboardResponse
-----------------

.. code-block:: python

   class DashboardResponse(BaseModel)

Поля и константы класса:

.. code-block:: python

   source: str
   date: str
   records: list[DashboardRecord]

