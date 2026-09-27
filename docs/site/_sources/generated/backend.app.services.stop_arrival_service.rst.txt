backend.app.services.stop_arrival_service
=========================================

Эвристическая оценка прибытия: три последовательных валидных медленных GPS-фиксации возле остановки. Радиус 35 м, скорость не выше 5 км/ч, серия длится 10–60 с. Возвращает принятое отклонение в секундах или None.

:download:`Скачать исходный код <../../backend/app/services/stop_arrival_service.py>`

StopArrivalService
------------------

.. code-block:: python

   class StopArrivalService

Поля и константы класса:

.. code-block:: python

   RADIUS_M = 35.0
   MAX_SPEED_KMH = 5.0
   MIN_DWELL_S = 10.0
   MAX_FIX_SPAN_S = 60.0
   MAX_SCHEDULE_OFFSET_S = 20 * 60

StopArrivalService.__init__
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def __init__(self, vehicle_state_service: VehicleStateService, schedule_service: ScheduleService, prediction_context_service: PredictionContextService) -> None

StopArrivalService.observe
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def observe(self, telemetry: TelemetryPoint) -> float | None

StopArrivalService._valid_slow_fix
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def _valid_slow_fix(self, point: TelemetryPoint) -> bool

StopArrivalService._distance_m
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def _distance_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float

