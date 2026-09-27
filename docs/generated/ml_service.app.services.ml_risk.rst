ml_service.app.services.ml_risk
===============================

Обучение классификатора риска, временное разбиение с исключением пересекающих границу ответов, оценка вероятностей, SHAP-объяснения регрессора, загрузка совместимых моделей и проверка конкурсного CSV. run_pipeline относится к исследовательской цепочке, не к каждому HTTP-запросу.

:download:`Скачать исходный код <../../ml_service/app/services/ml_risk.py>`

model_input
-----------

.. code-block:: python

   def model_input(frame, feature_names)

.. code-block:: text

   Select the persisted order; never use incidental DataFrame column order.

risk_target
-----------

.. code-block:: python

   def risk_target(points)

temporal_split
--------------

.. code-block:: python

   def temporal_split(points)

.. code-block:: text

   60/20/20 by unique train timestamps; purge labels crossing either boundary.

probability_metrics
-------------------

.. code-block:: python

   def probability_metrics(y, probability)

train_risk
----------

.. code-block:: python

   def train_risk(frame, points, feature_names)

predict_risk
------------

.. code-block:: python

   def predict_risk(classifier, metadata, frame)

scalar
------

.. code-block:: python

   def scalar(value)

explain_predictions
-------------------

.. code-block:: python

   def explain_predictions(regressor, frame, top_k=3)

.. code-block:: text

   Explain the correction; add cur_dev_s explicitly to recover absolute delay.

predict_for_frontend
--------------------

.. code-block:: python

   def predict_for_frontend(regressor, classifier, metadata, frame)

model_fingerprint
-----------------

.. code-block:: python

   def model_fingerprint(model)

.. code-block:: text

   Hash prediction structure, ignoring CatBoost build/time/GUID metadata.

load_models
-----------

.. code-block:: python

   def load_models(directory, regressor_path='final_model.cbm')

validate_submission
-------------------

.. code-block:: python

   def validate_submission(submission, points, template)

write_json
----------

.. code-block:: python

   def write_json(path, obj)

run_pipeline
------------

.. code-block:: python

   def run_pipeline(regressor, F_train, train, F_test, test, F_validate, validate, data, output_dir='ml_artifacts', regressor_path='final_model.cbm')

.. code-block:: text

   Train only risk; preserve the supplied regressor and existing root submission.

