ml_service.app.services.model_service
=====================================

Онлайн-инференс: загружает регрессор и классификатор риска, приводит словарь к фиксированному порядку FEATURE_COLS и нормализует категориальные пропуски. predict_details возвращает полный контракт API, predict — только predicted_delay_s.

:download:`Скачать исходный код <../../ml_service/app/services/model_service.py>`

ModelService
------------

.. code-block:: python

   class ModelService

ModelService.__init__
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def __init__(self) -> None

ModelService.predict
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def predict(self, features: dict[str, float | int | str | None]) -> float

ModelService.predict_details
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def predict_details(self, features: dict[str, float | int | str | None]) -> dict

