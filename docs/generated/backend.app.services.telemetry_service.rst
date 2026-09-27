backend.app.services.telemetry_service
======================================

Принимает нормализованную TelemetryPoint и передаёт её в хранилище истории. Используется общей цепочкой обработки HTTP и NDTP.

:download:`Скачать исходный код <../../backend/app/services/telemetry_service.py>`

TelemetryService
----------------

.. code-block:: python

   class TelemetryService

TelemetryService.__init__
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def __init__(self, vehicle_state_service: VehicleStateService) -> None

TelemetryService.process
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def process(self, telemetry: TelemetryPoint) -> None

