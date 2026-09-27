backend.app.services.prediction_service
=======================================

Собирает признаки по PredictionContext и вызывает ML /predict по HTTP с тайм-аутом 5 секунд. predict возвращает полный ответ ML; predict_delay извлекает только задержку в секундах. Адрес задаётся ML_SERVICE_URL.

:download:`Скачать исходный код <../../backend/app/services/prediction_service.py>`

PredictionService
-----------------

.. code-block:: python

   class PredictionService

PredictionService.__init__
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def __init__(self, feature_service: FeatureService, ml_service_url: str) -> None

PredictionService.predict
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   async def predict(self, context: PredictionContext) -> dict

PredictionService.predict_delay
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   async def predict_delay(self, context: PredictionContext) -> float

