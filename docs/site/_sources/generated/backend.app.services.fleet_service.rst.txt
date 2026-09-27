backend.app.services.fleet_service
==================================

Формирует текущие позиции всех наблюдаемых ТС, включая транспорт без прогноза. Объединяет свежесть GPS, курс, скорость, статистику окна и причину недоступности прогноза.

:download:`Скачать исходный код <../../backend/app/services/fleet_service.py>`

FleetService
------------

.. code-block:: python

   class FleetService

Поля и константы класса:

.. code-block:: python

   ACTIVE_WINDOW = timedelta(minutes=15)
   FRESH_WINDOW = timedelta(minutes=2)

FleetService.__init__
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def __init__(self, vehicle_state_service: VehicleStateService, schedule_service: ScheduleService, prediction_context_service: PredictionContextService, dashboard_service: DashboardService) -> None

FleetService.set_emulator_unit_ids
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def set_emulator_unit_ids(self, unit_ids: set[str]) -> None

FleetService.build_response
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def build_response(self, now: datetime | None=None) -> FleetResponse

