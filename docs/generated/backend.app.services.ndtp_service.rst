backend.app.services.ndtp_service
=================================

TCP-приёмник незашифрованного NDTP 6.2. Проверяет кадр и CRC, handshake и навигационную ячейку, преобразует GPS в TelemetryPoint и направляет его в ProcessingService. NdtpProtocolError обозначает неподдерживаемый или повреждённый кадр.

:download:`Скачать исходный код <../../backend/app/services/ndtp_service.py>`

NdtpProtocolError
-----------------

.. code-block:: python

   class NdtpProtocolError(ValueError)

crc16_modbus
------------

.. code-block:: python

   def crc16_modbus(data: bytes) -> int

_swapped
--------

.. code-block:: python

   def _swapped(value: int) -> int

decode_frame
------------

.. code-block:: python

   def decode_frame(header: bytes, payload: bytes) -> tuple[int, int, TelemetryPoint | None]

.. code-block:: text

   Return (unit_id, NPH type, navigation); handshake has no navigation.

NdtpServer
----------

.. code-block:: python

   class NdtpServer

NdtpServer.__init__
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def __init__(self, processing_service: ProcessingService, host: str, port: int) -> None

NdtpServer.start
~~~~~~~~~~~~~~~~

.. code-block:: python

   async def start(self) -> None

NdtpServer.close
~~~~~~~~~~~~~~~~

.. code-block:: python

   async def close(self) -> None

NdtpServer.register_unit
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def register_unit(self, unit_id: int, tr_id: str, *, manual: bool=False) -> None

NdtpServer.load_traffic_mappings
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def load_traffic_mappings(self, path: Path) -> tuple[int, int]

.. code-block:: text

   Read unit_id -> tr_id per day from the organizers' traffic CSV.

   A unit can be reused on another day. Conflicting IDs within one day
   are left unmapped, since picking one would attach GPS to the wrong trip.

NdtpServer.resolve_unit
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def resolve_unit(self, unit_id: int, event_time: datetime) -> str

NdtpServer.status
~~~~~~~~~~~~~~~~~

.. code-block:: python

   def status(self) -> dict

NdtpServer._handle_client
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None

