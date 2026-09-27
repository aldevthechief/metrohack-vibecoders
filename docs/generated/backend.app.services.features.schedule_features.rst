backend.app.services.features.schedule_features
===============================================

Календарные признаки, горизонт, текущее отклонение и число остановок до цели, вычисленные из PredictionContext и плана.

:download:`Скачать исходный код <../../backend/app/services/features/schedule_features.py>`

ScheduleFeatureService
----------------------

.. code-block:: python

   class ScheduleFeatureService

ScheduleFeatureService.__init__
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def __init__(self, schedule_service: ScheduleService) -> None

ScheduleFeatureService.build
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def build(self, context: PredictionContext) -> dict[str, float | int | str]

ScheduleFeatureService._calculate_stops_to_target
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def _calculate_stops_to_target(self, context: PredictionContext) -> int

