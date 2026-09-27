ml_service.app.models.prediction
================================

Контракты ML. PredictionRequest содержит features; PredictionResponse — задержку в секундах, вероятность события > 120 с, порог, метод вероятности и список вкладов признаков.

:download:`Скачать исходный код <../../ml_service/app/models/prediction.py>`

PredictionRequest
-----------------

.. code-block:: python

   class PredictionRequest(BaseModel)

Поля и константы класса:

.. code-block:: python

   features: dict[str, float | int | str | None]

PredictionResponse
------------------

.. code-block:: python

   class PredictionResponse(BaseModel)

Поля и константы класса:

.. code-block:: python

   predicted_delay_s: float
   delay_probability: float
   delay_threshold_sec: int
   probability_method: str
   reason_factors: list[dict]

