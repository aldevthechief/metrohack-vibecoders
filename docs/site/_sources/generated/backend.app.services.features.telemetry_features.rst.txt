backend.app.services.features.telemetry_features
================================================

Статистика скорости на окнах 30 с — 15 минут, простой при скорости ≤ 2 км/ч, динамика скорости и качество доставки пакетов. build принимает рейс и момент расчёта, возвращает словарь признаков без использования будущих пакетов.

:download:`Скачать исходный код <../../backend/app/services/features/telemetry_features.py>`

TelemetryFeatureService
-----------------------

.. code-block:: python

   class TelemetryFeatureService

Поля и константы класса:

.. code-block:: python

   STOP_SPEED_KMH = 2.0
   WINDOWS = {'30s': 30, '1m': 60, '3m': 180, '5m': 300, '10m': 600, '15m': 900}

TelemetryFeatureService.__init__
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def __init__(self, vehicle_state_service: VehicleStateService) -> None

TelemetryFeatureService.build
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def build(self, tr_id: str, at: datetime) -> dict[str, float | int | str | None]

TelemetryFeatureService._add_speed_statistics
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def _add_speed_statistics(result: dict[str, float | int | str | None], speeds: list[float], suffix: str) -> None

TelemetryFeatureService._max_packet_gap
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def _max_packet_gap(history: list[TelemetryPoint]) -> float | None

TelemetryFeatureService._speed_slope
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def _speed_slope(points: list[TelemetryPoint]) -> float | None

TelemetryFeatureService._longest_stop
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def _longest_stop(self, points: list[TelemetryPoint]) -> float | None

TelemetryFeatureService._stop_count
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def _stop_count(self, points: list[TelemetryPoint]) -> int

TelemetryFeatureService._time_since_last_move
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def _time_since_last_move(self, history: list[TelemetryPoint], at: datetime) -> float | None

TelemetryFeatureService._current_stop_duration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def _current_stop_duration(self, history: list[TelemetryPoint], at: datetime) -> float

