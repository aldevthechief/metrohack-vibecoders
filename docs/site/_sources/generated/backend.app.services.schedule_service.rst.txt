backend.app.services.schedule_service
=====================================

Хранит плановые остановки по рейсам, загружает CSV, ищет заданную цель и следующую остановку в допустимом прогнозном окне. Повторная загрузка заменяет остановки с теми же идентификаторами.

:download:`Скачать исходный код <../../backend/app/services/schedule_service.py>`

ScheduleService
---------------

.. code-block:: python

   class ScheduleService

ScheduleService.__init__
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def __init__(self) -> None

ScheduleService.add
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def add(self, point: SchedulePoint) -> None

ScheduleService.add_many
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def add_many(self, points: list[SchedulePoint]) -> None

ScheduleService.load_plan_csv
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def load_plan_csv(self, path: Path) -> int

.. code-block:: text

   Load planned stops; repeated loads replace the same stop IDs.

ScheduleService.get_trip_schedule
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def get_trip_schedule(self, tr_id: str) -> list[SchedulePoint]

ScheduleService.get_target
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def get_target(self, tr_id: str, target_stop_id: str) -> SchedulePoint | None

ScheduleService.get_next_target
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def get_next_target(self, tr_id: str, at: datetime) -> SchedulePoint | None

