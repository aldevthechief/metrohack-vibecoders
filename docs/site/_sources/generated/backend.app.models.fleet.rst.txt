backend.app.models.fleet
========================

Модели текущего парка независимо от наличия прогнозов. FleetVehicle содержит последнее положение, курс, скорость, статистику пакетов и состояние прогноза; FleetResponse добавляет время формирования ответа.

:download:`Скачать исходный код <../../backend/app/models/fleet.py>`

FleetVehicle
------------

.. code-block:: python

   class FleetVehicle(BaseModel)

Поля и константы класса:

.. code-block:: python

   vehicleId: str
   unitId: str | None = None
   source: str = 'ndtp'
   position: list[float] | None = None
   trail: list[list[float]] = Field(default_factory=list)
   telemetryTime: str | None = None
   gpsReceivedAt: str | None = None
   lastReceivedAt: str
   telemetryAgeSec: float | None = None
   speedKmh: float | None = None
   headingDeg: float | None = None
   packetCount15m: int = 0
   meanSpeed5mKmh: float | None = None
   stoppedFraction5m: float | None = None
   status: str
   predictionStatus: str

FleetResponse
-------------

.. code-block:: python

   class FleetResponse(BaseModel)

Поля и константы класса:

.. code-block:: python

   source: str = 'live-telemetry'
   generatedAt: str
   vehicles: list[FleetVehicle]

