backend.app.services.features.spatial_features
==============================================

Пространственные признаки по доступной истории GPS: возраст позиции, расстояние до цели и изменение расстояния на окнах. Отсутствующая позиция отражается через признаки доступности и пропуски.

:download:`Скачать исходный код <../../backend/app/services/features/spatial_features.py>`

SpatialFeatureService
---------------------

.. code-block:: python

   class SpatialFeatureService

Поля и константы класса:

.. code-block:: python

   EARTH_RADIUS_M = 6371008.8

SpatialFeatureService.__init__
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def __init__(self, vehicle_state_service: VehicleStateService) -> None

SpatialFeatureService.build
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def build(self, tr_id: str, at: datetime, target_longitude: float, target_latitude: float) -> dict[str, float | int | None]

SpatialFeatureService._has_valid_position
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def _has_valid_position(point) -> bool

SpatialFeatureService._haversine_m
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def _haversine_m(cls, lon1: float, lat1: float, lon2: float, lat2: float) -> float

