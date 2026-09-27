backend.app.services.vehicle_state_service
==========================================

Хранилище телеметрии в памяти, по умолчанию окно 15 минут. Сортирует пакеты по event_time. Выборка until исключает как будущие события, так и пакеты, которые ещё не были получены на момент прогноза.

:download:`Скачать исходный код <../../backend/app/services/vehicle_state_service.py>`

VehicleStateService
-------------------

.. code-block:: python

   class VehicleStateService

VehicleStateService.__init__
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def __init__(self, history_minutes: int=15) -> None

VehicleStateService.add
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def add(self, telemetry: TelemetryPoint) -> None

VehicleStateService.get_history
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def get_history(self, tr_id: str, until: datetime | None=None) -> list[TelemetryPoint]

VehicleStateService.get_latest
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def get_latest(self, tr_id: str, until: datetime | None=None) -> TelemetryPoint | None

VehicleStateService.get_vehicle_ids
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def get_vehicle_ids(self) -> list[str]

VehicleStateService._cleanup
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def _cleanup(self, tr_id: str, current_time: datetime) -> None

