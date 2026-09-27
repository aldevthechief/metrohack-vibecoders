backend.app.models.telemetry
============================

Входная телеметрия и соответствие устройства рейсу. TelemetryPoint хранит время события и получения отдельно, а также GPS, скорость и флаг истории. NdtpUnitMapping проверяет диапазон unit_id и непустой tr_id.

:download:`Скачать исходный код <../../backend/app/models/telemetry.py>`

TelemetryPoint
--------------

.. code-block:: python

   class TelemetryPoint(BaseModel)

Поля и константы класса:

.. code-block:: python

   packet_id: str | None = None
   tr_id: str
   unit_id: str | None = None
   event_time: datetime
   gps_time: datetime | None = None
   receive_time: datetime
   speed: float | None = None
   heading: float | None = None
   altitude: float | None = None
   location_valid: bool | None = None
   longitude: float | None = None
   latitude: float | None = None
   is_hist: bool = False

NdtpUnitMapping
---------------

.. code-block:: python

   class NdtpUnitMapping(BaseModel)

Поля и константы класса:

.. code-block:: python

   unit_id: int = Field(ge=0, le=2147483647)
   tr_id: str = Field(min_length=1)

