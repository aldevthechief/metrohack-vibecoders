backend.app.services.historical_replay_service
==============================================

Асинхронный прогон points и traffic через сборщик признаков и HTTP ML. История изолирована от живого потока. start возвращает состояние; status содержит прогресс, записи и ошибку при неуспехе.

:download:`Скачать исходный код <../../backend/app/services/historical_replay_service.py>`

HistoricalReplayService
-----------------------

.. code-block:: python

   class HistoricalReplayService

HistoricalReplayService.__init__
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def __init__(self, schedule: ScheduleService, points_path: Path, traffic_path: Path, ml_url: str) -> None

HistoricalReplayService.start
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def start(self) -> dict

HistoricalReplayService.status
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def status(self) -> dict

HistoricalReplayService._read_inputs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def _read_inputs(self)

HistoricalReplayService._run
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   async def _run(self) -> None

