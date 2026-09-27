backend.app.models.incident
===========================

Контракт инцидента: целевая остановка, текущее отклонение, задержка в секундах, вероятность события, уровень риска и наблюдаемые сигналы. RiskLevel содержит low, medium и high.

:download:`Скачать исходный код <../../backend/app/models/incident.py>`

RiskLevel
---------

.. code-block:: python

   class RiskLevel(str, Enum)

Поля и константы класса:

.. code-block:: python

   LOW = 'low'
   MEDIUM = 'medium'
   HIGH = 'high'

Incident
--------

.. code-block:: python

   class Incident(BaseModel)

Поля и константы класса:

.. code-block:: python

   tr_id: str
   target_stop_id: str
   current_time: datetime
   current_deviation_s: float
   current_deviation_source: str | None = None
   predicted_delay_s: float
   delay_probability: float | None = None
   reason_factors: list[dict] = Field(default_factory=list)
   risk_level: RiskLevel
   signal: str
   speed_kmh: float | None = None
   mean_speed_kmh: float | None = None
   stop_fraction: float | None = None

