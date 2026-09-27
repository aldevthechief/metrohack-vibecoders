backend.app.services.ndtp_emulator_service
==========================================

Фоновая поддержка конфигурации необязательного эмулятора через HTTP. Сравнивает устройства и повторяет настройку после ошибок связи или перезапуска эмулятора.

:download:`Скачать исходный код <../../backend/app/services/ndtp_emulator_service.py>`

_unit_settings
--------------

.. code-block:: python

   def _unit_settings(units: list[dict]) -> set[tuple[int, int, bool]]

maintain_emulator
-----------------

.. code-block:: python

   async def maintain_emulator(url: str, config: dict) -> None

