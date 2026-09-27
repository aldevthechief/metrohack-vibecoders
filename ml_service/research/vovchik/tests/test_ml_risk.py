"""Run with: python -m unittest discover -s tests -v."""
import json
import tempfile
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
from catboost import CatBoostRegressor
from ml_service.app.services.ml_risk import (CATEGORICAL, explain_predictions, model_input, risk_target,
                     temporal_split, validate_submission, train_risk, predict_risk, model_fingerprint)


class RiskContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        n = 100
        cls.frame = pd.DataFrame({"sample_id": [str(i) for i in range(n)],
            "tr_id": [str(i % 4) for i in range(n)], "target_stop_id": [str(i % 7) for i in range(n)],
            "unit_id": [None if i % 9 == 0 else str(i % 4) for i in range(n)],
            "cur_dev_s": np.arange(n) * 3., "speed_now": np.where(np.arange(n) % 8 == 0, np.nan, np.arange(n) % 40)})
        cls.names = CATEGORICAL + ["cur_dev_s", "speed_now"]
        cls.model = CatBoostRegressor(iterations=12, depth=3, verbose=False, allow_writing_files=False, thread_count=2)
        cls.model.fit(model_input(cls.frame, cls.names), np.sin(np.arange(n)) * 30, cat_features=CATEGORICAL)
        cls.points = pd.DataFrame({"T": pd.date_range('2026-01-01', periods=n, freq='5min'),
            "target_time_begin": pd.date_range('2026-01-01 00:12', periods=n, freq='5min'),
            "target_delay_s": np.where(np.arange(n) % 3 == 0, 180., 20.)})

    def test_threshold_is_strictly_greater(self):
        np.testing.assert_array_equal(risk_target(pd.DataFrame({'target_delay_s': [119, 120, 121]})), [0, 0, 1])

    def test_temporal_partitions_and_label_purge(self):
        fit, cal, select, cal_start, select_start = temporal_split(self.points)
        self.assertFalse(set(fit) & set(cal) or set(fit) & set(select) or set(cal) & set(select))
        known = self.points.target_time_begin + pd.to_timedelta(self.points.target_delay_s, unit='s')
        self.assertTrue((known.iloc[fit] < cal_start).all())
        self.assertTrue((known.iloc[cal] < select_start).all())
        self.assertTrue((self.points['T'].iloc[cal] >= cal_start).all())
        self.assertTrue((self.points['T'].iloc[select] >= select_start).all())

    def test_shap_order_nulls_and_additivity(self):
        a = explain_predictions(self.model, self.frame.head(8))
        b = explain_predictions(self.model, self.frame.head(8)[list(reversed(self.frame.columns))])
        self.assertEqual(a, b)
        for record in a:
            e = record['explanation']
            self.assertLessEqual(len(e['factors']), 3)
            self.assertGreaterEqual(len(e['factors']), 1)
            actual = e['currentDeviationSec'] + e['baseValueSec'] + e['remainingShapValueSec'] + sum(f['shapValueSec'] for f in e['factors'])
            self.assertAlmostEqual(actual, record['predictionSec'], places=7)
            self.assertTrue(all({'feature','label','value','shapValueSec'} <= set(f) for f in e['factors']))
        json.dumps(a, allow_nan=False)

    def test_model_identity_ignores_metadata_but_checks_prediction_structure(self):
        clone = self.model.copy()
        clone.get_metadata()["audit_note"] = "Different serialization metadata"
        self.assertEqual(model_fingerprint(self.model), model_fingerprint(clone))
        scale, bias = clone.get_scale_and_bias()
        clone.set_scale_and_bias(scale, bias + 10.)
        self.assertNotEqual(model_fingerprint(self.model), model_fingerprint(clone))

    def test_missing_feature_fails(self):
        with self.assertRaises(ValueError):
            explain_predictions(self.model, self.frame.drop(columns='speed_now'))

    def test_risk_roundtrip(self):
        from catboost import CatBoostClassifier
        risk, meta = train_risk(self.frame, self.points, self.names)
        p = predict_risk(risk, meta, self.frame)
        self.assertTrue(((p >= 0) & (p <= 1)).all())
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / 'risk.cbm')
            risk.save_model(path)
            restored = CatBoostClassifier().load_model(path)
            np.testing.assert_array_equal(p, predict_risk(restored, json.loads(json.dumps(meta)), self.frame))

    def test_submission_rejects_wrong_ids_duplicates_and_nan(self):
        template = pd.DataFrame({'sample_id': ['a', 'b']})
        correct = template.assign(prediction=[10., -5.])
        validate_submission(correct, template, template)
        for bad in [correct.assign(sample_id=['a','a']), correct.assign(sample_id=['a','x']),
                    correct.assign(prediction=[10., np.nan]), correct.assign(extra=1)]:
            with self.assertRaises(ValueError):
                validate_submission(bad, template, template)


if __name__ == '__main__':
    unittest.main()
