backend.app.models.schedule
===========================

Входные контракты расписания и прогнозного контекста. SchedulePoint задаёт остановку и плановое время; PredictionContext — момент прогноза, цель и текущее отклонение; ObservedArrival — фактическое прибытие.

:download:`Скачать исходный код <../../backend/app/models/schedule.py>`

SchedulePoint
-------------

.. code-block:: python

   class SchedulePoint(BaseModel)

Поля и константы класса:

.. code-block:: python

   tr_id: str
   stop_id: str
   time_begin: datetime
   longitude: float | None = None
   latitude: float | None = None
   address: str | None = None

PredictionContext
-----------------

.. code-block:: python

   class PredictionContext(BaseModel)

Поля и константы класса:

.. code-block:: python

   tr_id: str
   target_stop_id: str
   current_time: datetime
   target_time_begin: datetime
   cur_dev_s: float

CurrentDeviation
----------------

.. code-block:: python

   class CurrentDeviation(BaseModel)

Поля и константы класса:

.. code-block:: python

   tr_id: str
   cur_dev_s: float

ObservedArrival
---------------

.. code-block:: python

   class ObservedArrival(BaseModel)

Поля и константы класса:

.. code-block:: python

   tr_id: str
   stop_id: str
   actual_time: datetime

