backend.app.services.dashboard_service
======================================

Преобразует инциденты и историю GPS в DashboardRecord, собирает маршрут, след ТС, адрес цели и показатели для карты. Хранит прогнозные записи в памяти и формирует DashboardResponse.

:download:`Скачать исходный код <../../backend/app/services/dashboard_service.py>`

DashboardService
----------------

.. code-block:: python

   class DashboardService

DashboardService.__init__
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def __init__(self, vehicle_state_service: VehicleStateService, schedule_service: ScheduleService) -> None

DashboardService.record_incident
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def record_incident(self, incident: Incident) -> None

DashboardService.get_records
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def get_records(self) -> list[DashboardRecord]

DashboardService.build_record
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def build_record(self, incident: Incident) -> DashboardRecord

DashboardService.build_response
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def build_response(self, records: list[DashboardRecord]) -> DashboardResponse

DashboardService._build_route
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def _build_route(self, tr_id: str) -> list[list[float]]

DashboardService._segment_label
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def _segment_label(self, tr_id: str, target_stop_id: str) -> str

