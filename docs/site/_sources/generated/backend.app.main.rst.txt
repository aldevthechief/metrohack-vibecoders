backend.app.main
================

Точка сборки Backend: создаёт сервисы, регистрирует HTTP-маршруты и управляет жизненным циклом NDTP. Контракты маршрутов доступны в разделе API.

:download:`Скачать исходный код <../../backend/app/main.py>`

lifespan
--------

.. code-block:: python

   async def lifespan(_: FastAPI)

root
----

.. code-block:: python

   async def root() -> RedirectResponse

health
------

.. code-block:: python

   async def health() -> dict[str, str]

add_telemetry
-------------

.. code-block:: python

   async def add_telemetry(telemetry: TelemetryPoint) -> dict

register_ndtp_unit
------------------

.. code-block:: python

   async def register_ndtp_unit(mapping: NdtpUnitMapping) -> dict[str, str]

get_ndtp_status
---------------

.. code-block:: python

   async def get_ndtp_status() -> dict

start_historical_replay
-----------------------

.. code-block:: python

   async def start_historical_replay() -> dict

get_historical_replay
---------------------

.. code-block:: python

   async def get_historical_replay() -> dict

get_vehicles
------------

.. code-block:: python

   async def get_vehicles() -> list[str]

get_fleet
---------

.. code-block:: python

   async def get_fleet() -> FleetResponse

get_latest_telemetry
--------------------

.. code-block:: python

   async def get_latest_telemetry(tr_id: str) -> TelemetryPoint

get_vehicle_history
-------------------

.. code-block:: python

   async def get_vehicle_history(tr_id: str) -> list[TelemetryPoint]

add_schedule_point
------------------

.. code-block:: python

   async def add_schedule_point(point: SchedulePoint) -> dict[str, str]

get_schedule
------------

.. code-block:: python

   async def get_schedule(tr_id: str) -> list[SchedulePoint]

set_current_deviation
---------------------

.. code-block:: python

   async def set_current_deviation(deviation: CurrentDeviation) -> dict[str, str]

record_arrival
--------------

.. code-block:: python

   async def record_arrival(arrival: ObservedArrival) -> dict[str, str | float]

set_prediction_context
----------------------

.. code-block:: python

   async def set_prediction_context(context: PredictionContext) -> dict[str, str]

get_telemetry_features
----------------------

.. code-block:: python

   async def get_telemetry_features(tr_id: str, at: str) -> dict

get_schedule_features
---------------------

.. code-block:: python

   async def get_schedule_features(context: PredictionContext) -> dict

get_spatial_features
--------------------

.. code-block:: python

   async def get_spatial_features(tr_id: str, at: str, target_longitude: float, target_latitude: float) -> dict

get_features
------------

.. code-block:: python

   async def get_features(context: PredictionContext) -> dict

predict
-------

.. code-block:: python

   async def predict(context: PredictionContext) -> dict

evaluate_incident
-----------------

.. code-block:: python

   async def evaluate_incident(context: PredictionContext) -> Incident

get_incidents
-------------

.. code-block:: python

   async def get_incidents() -> list[Incident]

get_vehicle_incident
--------------------

.. code-block:: python

   async def get_vehicle_incident(tr_id: str) -> Incident

get_dashboard
-------------

.. code-block:: python

   async def get_dashboard() -> DashboardResponse

