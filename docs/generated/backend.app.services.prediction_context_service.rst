backend.app.services.prediction_context_service
===============================================

Хранилище текущего отклонения, источника измерения и прогнозного контекста для рейса. Используется при ручной передаче отклонения, подтверждённом прибытии и GPS-оценке.

:download:`Скачать исходный код <../../backend/app/services/prediction_context_service.py>`

PredictionContextService
------------------------

.. code-block:: python

   class PredictionContextService

PredictionContextService.__init__
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def __init__(self) -> None

PredictionContextService.set
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def set(self, context: PredictionContext) -> None

PredictionContextService.update_context
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def update_context(self, context: PredictionContext) -> None

PredictionContextService.set_current_deviation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def set_current_deviation(self, tr_id: str, cur_dev_s: float, source: str='provided', observed_at: datetime | None=None) -> bool

PredictionContextService.get_current_deviation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def get_current_deviation(self, tr_id: str) -> float | None

PredictionContextService.get_current_deviation_source
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def get_current_deviation_source(self, tr_id: str) -> str | None

PredictionContextService.get
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def get(self, tr_id: str) -> PredictionContext | None

PredictionContextService.remove
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def remove(self, tr_id: str) -> None

PredictionContextService.get_all
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def get_all(self) -> list[PredictionContext]

