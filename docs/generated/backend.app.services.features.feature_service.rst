backend.app.services.features.feature_service
=============================================

Объединяет признаки трёх групп. build проверяет зарегистрированную цель, её время, координаты и горизонт (600, 900] секунд; при нарушении условий выбрасывает ValueError.

:download:`Скачать исходный код <../../backend/app/services/features/feature_service.py>`

FeatureService
--------------

.. code-block:: python

   class FeatureService

FeatureService.__init__
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def __init__(self, schedule_feature_service: ScheduleFeatureService, spatial_feature_service: SpatialFeatureService, telemetry_feature_service: TelemetryFeatureService, schedule_service: ScheduleService) -> None

FeatureService.build
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def build(self, context: PredictionContext) -> dict[str, float | int | str | None]

