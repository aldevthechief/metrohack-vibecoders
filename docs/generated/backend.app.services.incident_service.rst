backend.app.services.incident_service
=====================================

Создаёт и хранит последний инцидент для рейса. Уровни риска определяются задержкой: low < 60 с, medium 60–120 с, high > 120 с. Вероятность ML и SHAP-факторы передаются отдельно; сигнал выбирается по наблюдаемым признакам.

:download:`Скачать исходный код <../../backend/app/services/incident_service.py>`

IncidentService
---------------

.. code-block:: python

   class IncidentService

Поля и константы класса:

.. code-block:: python

   MEDIUM_DELAY_S = 60.0
   HIGH_DELAY_S = 120.0
   CURRENT_DEVIATION_SIGNAL_S = 120.0
   LONG_STOP_FRACTION = 0.7
   LOW_MEAN_SPEED_KMH = 10.0

IncidentService.__init__
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def __init__(self, feature_service: FeatureService) -> None

IncidentService.process
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def process(self, context: PredictionContext, predicted_delay_s: float, current_deviation_source: str | None=None, delay_probability: float | None=None, reason_factors: list[dict] | None=None) -> Incident

IncidentService.get_all
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def get_all(self) -> list[Incident]

IncidentService.get_by_vehicle
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def get_by_vehicle(self, tr_id: str) -> Incident | None

IncidentService._calculate_risk
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def _calculate_risk(self, predicted_delay_s: float) -> RiskLevel

IncidentService._detect_signal
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def _detect_signal(self, current_deviation_s: float, mean_speed_kmh: float | None, stop_fraction: float | None) -> str

IncidentService._to_float
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def _to_float(value: object) -> float | None

