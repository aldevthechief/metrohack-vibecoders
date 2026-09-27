ml_service.app.main
===================

FastAPI-приложение ML с маршрутами /health и /predict. При импорте создаёт ModelService и загружает существующие артефакты; обучение здесь не запускается.

:download:`Скачать исходный код <../../ml_service/app/main.py>`

root
----

.. code-block:: python

   async def root() -> RedirectResponse

health
------

.. code-block:: python

   async def health() -> dict[str, str]

predict
-------

.. code-block:: python

   async def predict(request: PredictionRequest) -> PredictionResponse

