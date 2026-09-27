backend.app.services.processing_service
=======================================

Оркестрация одного пакета: сохранить телеметрию, оценить прибытие, выбрать цель и отклонение, вызвать ML, создать инцидент и обновить дашборд. process_telemetry возвращает Incident либо None при отсутствии условий прогноза.

:download:`Скачать исходный код <../../backend/app/services/processing_service.py>`

ProcessingService
-----------------

.. code-block:: python

   class ProcessingService

ProcessingService.__init__
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def __init__(self, telemetry_service: TelemetryService, prediction_context_service: PredictionContextService, prediction_service: PredictionService, incident_service: IncidentService, dashboard_service: DashboardService, schedule_service: ScheduleService, stop_arrival_service: StopArrivalService) -> None

ProcessingService.process_telemetry
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   async def process_telemetry(self, telemetry: TelemetryPoint) -> Incident | None

