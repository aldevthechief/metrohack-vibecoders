"""Risk training and per-prediction regression explanations on existing features."""
from pathlib import Path
import hashlib
import json
import tempfile

import numpy as np
import pandas as pd
from catboost import CatBoostClassifier, CatBoostRegressor, Pool
from scipy.special import expit
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, brier_score_loss,
                             confusion_matrix, log_loss, roc_auc_score)

THRESHOLD_SEC = 120
CATEGORICAL = ["tr_id", "target_stop_id", "unit_id"]
LABELS = {
    "tr_id": "Идентификатор транспортного средства",
    "target_stop_id": "Идентификатор целевой остановки",
    "unit_id": "Идентификатор бортового устройства",
    "hour": "Час прогноза", "minute": "Минута часа",
    "minute_of_day": "Минута суток", "day_of_week": "День недели",
    "is_weekend": "Выходной день", "sin_time": "Время суток: синус",
    "cos_time": "Время суток: косинус", "target_hour": "Час целевого прибытия",
    "target_minute_of_day": "Минута суток целевого прибытия",
    "forecast_horizon_s": "Время до целевой остановки, с",
    "cur_dev_s": "Текущее отклонение от расписания, с",
    "abs_cur_dev": "Модуль текущего отклонения, с",
    "is_late_now": "ТС сейчас опаздывает", "is_early_now": "ТС сейчас опережает график",
    "stops_to_target": "Число плановых остановок до цели",
    "sp_has_position": "Есть достоверная позиция",
    "sp_position_age_s": "Возраст координат, с",
    "sp_distance_to_target_m": "Расстояние по прямой до цели, м",
    "event_time": "Время последнего события, Unix-секунды",
    "receive_time": "Время получения последнего пакета, Unix-секунды",
    "gps_time": "Время GPS последнего пакета, Unix-секунды",
    "speed_now": "Последняя известная скорость, км/ч",
    "telemetry_age": "Возраст телеметрии, с", "gps_age": "Возраст GPS, с",
    "receive_delay": "Задержка доставки последнего пакета, с",
    "last_packet_is_hist": "Последний пакет исторический",
    "packet_count_15m": "Число пакетов за 15 мин",
    "packet_frequency": "Число пакетов в минуту за 15 мин",
    "hist_packet_fraction": "Доля исторических пакетов за 15 мин",
    "mean_receive_delay": "Средняя задержка доставки за 15 мин, с",
    "max_packet_gap": "Максимальный интервал между пакетами за 15 мин, с",
    "longest_stop_5m": "Самый долгий простой за 5 мин, с",
    "stop_count_10m": "Число остановок за 10 мин",
    "time_since_last_move": "Время с последнего движения, с",
    "current_stop_duration": "Текущая продолжительность простоя, с",
}
for window, label in {"30s": "30 с", "1m": "1 мин", "3m": "3 мин",
                      "5m": "5 мин", "10m": "10 мин", "15m": "15 мин"}.items():
    for stat, name in {"mean": "Средняя", "std": "Стандартное отклонение скорости",
                       "min": "Минимальная", "max": "Максимальная", "median": "Медианная"}.items():
        LABELS[f"speed_{stat}_{window}"] = (f"{name} скорость за {label}, км/ч" if stat != "std"
                                            else f"{name} за {label}, км/ч")
    if window in ("1m", "3m", "5m"):
        LABELS[f"stopped_fraction_{window}"] = f"Доля простоя за {label}"
        LABELS[f"speed_slope_{window}"] = f"Изменение скорости за {label}, км/ч в минуту"
for minutes in (1, 3):
    LABELS[f"sp_approach_{minutes}m_m"] = f"Приближение к цели за {minutes} мин, м"
    LABELS[f"sp_approach_speed_{minutes}m_mps"] = f"Скорость приближения за {minutes} мин, м/с"


def model_input(frame, feature_names):
    """Select the persisted order; never use incidental DataFrame column order."""
    missing = set(feature_names) - set(frame.columns)
    if missing:
        raise ValueError(f"Missing features: {sorted(missing)}")
    x = frame.loc[:, feature_names].copy()
    for col in CATEGORICAL:
        x[col] = x[col].fillna("missing").astype(str)
    return x


def risk_target(points):
    return points["target_delay_s"].gt(THRESHOLD_SEC).astype(int).to_numpy()


def temporal_split(points):
    """60/20/20 by unique train timestamps; purge labels crossing either boundary."""
    times = pd.to_datetime(points["T"], format="mixed")
    unique = times.sort_values().unique()
    calibration_start = pd.Timestamp(unique[int(len(unique) * 0.60)])
    selection_start = pd.Timestamp(unique[int(len(unique) * 0.80)])
    target = pd.to_datetime(points["target_time_begin"], format="mixed")
    available = target + pd.to_timedelta(points["target_delay_s"].clip(lower=0), unit="s")
    fit = np.flatnonzero(((times < calibration_start) & (available < calibration_start)).to_numpy())
    calibration = np.flatnonzero(((times >= calibration_start) & (times < selection_start)
                                  & (available < selection_start)).to_numpy())
    selection = np.flatnonzero((times >= selection_start).to_numpy())
    y = risk_target(points)
    for name, idx in [("fit", fit), ("calibration", calibration), ("selection", selection)]:
        if len(idx) == 0 or len(np.unique(y[idx])) != 2:
            raise ValueError(f"Temporal {name} split must contain both classes")
    return fit, calibration, selection, calibration_start, selection_start


def probability_metrics(y, probability):
    bins = []
    ece = 0.0
    bucket = np.minimum((probability * 10).astype(int), 9)
    for i in range(10):
        mask = bucket == i
        count = int(mask.sum())
        mean = float(probability[mask].mean()) if count else None
        actual = float(y[mask].mean()) if count else None
        if count:
            ece += count / len(y) * abs(mean - actual)
        bins.append({"lower": i / 10, "upper": (i + 1) / 10, "count": count,
                     "meanProbability": mean, "observedFrequency": actual})
    return {
        "rocAuc": float(roc_auc_score(y, probability)) if len(np.unique(y)) == 2 else None,
        "averagePrecision": float(average_precision_score(y, probability)) if y.sum() else None,
        "brier": float(brier_score_loss(y, probability)),
        "logLoss": float(log_loss(y, probability, labels=[0, 1])),
        "ece10": float(ece), "calibrationBins": bins,
        "confusionMatrixAt05": confusion_matrix(y, probability >= 0.5, labels=[0, 1]).tolist(),
    }


def train_risk(frame, points, feature_names):
    x = model_input(frame, feature_names)
    y = risk_target(points)
    fit, calibration, selection, calibration_start, selection_start = temporal_split(points)
    classifier = CatBoostClassifier(iterations=400, depth=6, learning_rate=0.05,
        loss_function="Logloss", random_seed=42, verbose=False, allow_writing_files=False,
        thread_count=4)
    classifier.fit(x.iloc[fit], y[fit], cat_features=CATEGORICAL)
    margin = classifier.predict(x.iloc[calibration], prediction_type="RawFormulaVal")
    sigmoid = LogisticRegression(C=1e6, solver="lbfgs", max_iter=1000)
    sigmoid.fit(np.asarray(margin).reshape(-1, 1), y[calibration])
    slope, intercept = float(sigmoid.coef_[0, 0]), float(sigmoid.intercept_[0])
    selection_margin = classifier.predict(x.iloc[selection], prediction_type="RawFormulaVal")
    raw_brier = brier_score_loss(y[selection], expit(selection_margin))
    sigmoid_brier = brier_score_loss(y[selection], expit(slope * selection_margin + intercept))
    selected = "sigmoid" if slope > 0 and sigmoid_brier < raw_brier else "raw"
    meta = {"schemaVersion": 1, "event": "target_delay_s > 120", "thresholdSec": THRESHOLD_SEC,
        "featureNames": list(feature_names), "categoricalFeatures": CATEGORICAL,
        "calibration": {"method": "sigmoid_on_raw_margin",
                        "slope": slope, "intercept": intercept, "selected": selected,
                        "selectionBrierRaw": float(raw_brier), "selectionBrierSigmoid": float(sigmoid_brier)},
        "split": {"method": "temporal_train_only_with_label_availability_purge",
                  "calibrationStart": calibration_start.isoformat(), "selectionStart": selection_start.isoformat(),
                  "fitRows": len(fit), "selectionRows": len(selection),
                  "calibrationRows": len(calibration), "purgedRows": len(points)-len(fit)-len(calibration)-len(selection),
                  "fitPositive": int(y[fit].sum()), "calibrationPositive": int(y[calibration].sum()), "selectionPositive": int(y[selection].sum())}}
    return classifier, meta


def predict_risk(classifier, metadata, frame):
    names = metadata["featureNames"]
    if classifier.feature_names_ != names:
        raise ValueError("Classifier feature order differs from metadata")
    margin = classifier.predict(model_input(frame, names), prediction_type="RawFormulaVal")
    cal = metadata["calibration"]
    p = expit(cal["slope"] * np.asarray(margin) + cal["intercept"]) if cal["selected"] == "sigmoid" else expit(margin)
    if not np.isfinite(p).all():
        raise ValueError("Risk probabilities are not finite")
    return p


def scalar(value):
    if pd.isna(value):
        return None
    return value.item() if isinstance(value, np.generic) else value


def explain_predictions(regressor, frame, top_k=3):
    """Explain the correction; add cur_dev_s explicitly to recover absolute delay."""
    if top_k not in (1, 2, 3):
        raise ValueError("top_k must be 1, 2, or 3")
    names = regressor.feature_names_
    x = model_input(frame, names)
    if set(names) - LABELS.keys():
        raise ValueError("Missing human-readable feature labels")
    correction = np.asarray(regressor.predict(x))
    shap = np.asarray(regressor.get_feature_importance(
        Pool(x, cat_features=CATEGORICAL), type="ShapValues", thread_count=4))
    np.testing.assert_allclose(shap[:, :-1].sum(axis=1) + shap[:, -1], correction,
                               rtol=1e-9, atol=1e-7)
    current = frame["cur_dev_s"].to_numpy(dtype=float)
    records = []
    for i, (_, row) in enumerate(frame.iterrows()):
        values = shap[i, :-1]
        ranked = np.argsort(-np.abs(values), kind="stable")
        selected = [j for j in ranked if abs(values[j]) > 1e-9][:top_k]
        factors = [{"feature": names[j], "label": LABELS[names[j]],
                    "value": scalar(x.iloc[i, j]), "shapValueSec": float(values[j])}
                   for j in selected]
        remaining = float(values.sum() - sum(item["shapValueSec"] for item in factors))
        base = float(shap[i, -1])
        prediction = float(current[i] + correction[i])
        np.testing.assert_allclose(current[i] + base + remaining
            + sum(item["shapValueSec"] for item in factors), prediction, rtol=1e-9, atol=1e-7)
        records.append({"sampleId": str(row["sample_id"]), "predictionSec": prediction,
            "predicted_delay_s": prediction, "explanation": {
                "method": "TreeSHAP", "explains": "regression_correction_seconds",
                "currentDeviationSec": float(current[i]), "baseValueSec": base,
                "remainingShapValueSec": remaining, "factors": factors}})
    return records


def predict_for_frontend(regressor, classifier, metadata, frame):
    if regressor.feature_names_ != metadata["featureNames"]:
        raise ValueError("Regressor and classifier feature schemas differ")
    records = explain_predictions(regressor, frame)
    for record, p in zip(records, predict_risk(classifier, metadata, frame)):
        record.update(delayProbability=float(p), delayThresholdSec=THRESHOLD_SEC,
                      probabilityMethod=metadata["calibration"]["selected"])
    return records


def model_fingerprint(model):
    """Hash prediction structure, ignoring CatBoost build/time/GUID metadata."""
    with tempfile.TemporaryDirectory(prefix="metrohack-model-check-") as directory:
        path = Path(directory) / "model.json"
        model.save_model(str(path), format="json")
        content = json.loads(path.read_text())
    content.pop("model_info", None)
    canonical = json.dumps(content, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def load_models(directory, regressor_path="final_model.cbm"):
    directory, regressor_path = Path(directory), Path(regressor_path)
    metadata = json.loads((directory / "risk_metadata.json").read_text())
    regressor = CatBoostRegressor().load_model(str(regressor_path))
    fingerprint = metadata.get("regressorFingerprint")
    matches = (model_fingerprint(regressor) == fingerprint if fingerprint else
               hashlib.sha256(regressor_path.read_bytes()).hexdigest() == metadata["regressorSha256"])
    if not matches:
        raise ValueError("Regressor changed; regenerate risk artifacts for this model")
    classifier = CatBoostClassifier().load_model(str(directory / "risk_model.cbm"))
    return regressor, classifier, metadata


def validate_submission(submission, points, template):
    if list(submission.columns) != ["sample_id", "prediction"]:
        raise ValueError("Submission must contain exactly sample_id,prediction")
    for data in (submission, points, template):
        if data["sample_id"].isna().any() or not data["sample_id"].is_unique:
            raise ValueError("Missing or duplicate sample_id")
    ids = set(submission["sample_id"])
    if ids != set(points["sample_id"]) or ids != set(template["sample_id"]):
        raise ValueError("Submission IDs do not match validate points and template")
    if not np.isfinite(submission["prediction"].to_numpy(dtype=float)).all():
        raise ValueError("Submission predictions must be finite")


def write_json(path, obj):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False)+"\n", encoding="utf-8")


def run_pipeline(regressor, F_train, train, F_test, test, F_validate, validate,
                 data, output_dir="ml_artifacts", regressor_path="final_model.cbm"):
    """Train only risk; preserve the supplied regressor and existing root submission."""
    data, output = Path(data), Path(output_dir)
    for frame, points in [(F_train, train), (F_test, test), (F_validate, validate)]:
        if not frame["sample_id"].reset_index(drop=True).equals(points["sample_id"].reset_index(drop=True)):
            raise ValueError("Feature rows and labels are not aligned")
    for left, right in [(train, test), (train, validate), (test, validate)]:
        if set(left["sample_id"]) & set(right["sample_id"]):
            raise ValueError("Dataset splits share sample IDs")
    classifier, metadata = train_risk(F_train, train, regressor.feature_names_)
    metadata["regressorSha256"] = hashlib.sha256(Path(regressor_path).read_bytes()).hexdigest()
    saved = CatBoostRegressor().load_model(str(regressor_path))
    metadata["schemaVersion"] = 2
    metadata["regressorFingerprint"] = model_fingerprint(regressor)
    if model_fingerprint(saved) != metadata["regressorFingerprint"]:
        raise ValueError("In-memory regressor differs from the saved model")
    test_prediction = F_test["cur_dev_s"].to_numpy() + regressor.predict(model_input(F_test, regressor.feature_names_))
    raw = classifier.predict_proba(model_input(F_test, metadata["featureNames"]))[:, 1]
    selected_probability = predict_risk(classifier, metadata, F_test)
    margin = classifier.predict(model_input(F_test, metadata["featureNames"]), prediction_type="RawFormulaVal")
    cal = metadata["calibration"]
    calibrated = expit(cal["slope"] * margin + cal["intercept"])
    y = risk_target(test)
    report = {"testRows": len(test), "testPositive": int(y.sum()),
        "testEventRate": float(y.mean()), "regressionMaeSec": float(np.abs(test_prediction-test["target_delay_s"].to_numpy()).mean()),
        "currentDeviationBaselineMaeSec": float(np.abs(test["cur_dev_s"]-test["target_delay_s"]).mean()),
        "riskRaw": probability_metrics(y, raw), "riskSigmoid": probability_metrics(y, calibrated),
        "riskSelected": probability_metrics(y, selected_probability), "probabilityMethod": cal["selected"],
        "riskConstantTrainPrior": probability_metrics(y, np.full(len(y), risk_target(train).mean())),
        "split": metadata["split"],
        "limitations": ["Official test points share vehicles and dates with train; this is not a future-day or unseen-vehicle evaluation.",
                         "Calibration and probability-method selection use separate temporal subsets of train. Test was evaluated during development; metrics are diagnostic, not a blind final estimate.",
                         "SHAP explains regression correction, not classifier risk or causal reasons for delays."]}
    records = predict_for_frontend(regressor, classifier, metadata, F_validate)
    template = pd.read_csv(data / "sample_submission.csv", sep=";", dtype={"sample_id": str})
    pred = pd.DataFrame({"sample_id": [r["sampleId"] for r in records],
                         "prediction": [r["predictionSec"] for r in records]})
    submission = template[["sample_id"]].merge(pred, on="sample_id", how="left", validate="one_to_one")
    validate_submission(submission, validate, template)
    output.mkdir(parents=True, exist_ok=True)
    classifier.save_model(str(output / "risk_model.cbm"))
    write_json(output / "risk_metadata.json", metadata)
    write_json(output / "metrics.json", report)
    write_json(output / "predictions_validate.json", {"schemaVersion": 1, "records": records})
    pd.DataFrame({"sample_id": test["sample_id"], "actual_delay_s": test["target_delay_s"],
        "predicted_delay_s": test_prediction, "absolute_error_s": np.abs(test_prediction-test["target_delay_s"].to_numpy()),
        "is_late": y, "raw_probability": raw, "delay_probability": selected_probability}).to_csv(output / "test_predictions.csv", index=False)
    submission.to_csv(output / "submission.csv", sep=";", index=False)
    submission.to_csv(data / "submission.csv", sep=";", index=False)
    validate_submission(pd.read_csv(data / "submission.csv", sep=";", dtype={"sample_id": str}), validate, template)
    print(f"Test MAE: {report['regressionMaeSec']:.4f} s; validate rows: {len(records)}")
    for name in ("riskRaw", "riskSigmoid", "riskSelected"):
        m = report[name]
        print(f"{name}: ROC-AUC={m['rocAuc']:.4f}; AP={m['averagePrecision']:.4f}; Brier={m['brier']:.4f}; ECE={m['ece10']:.4f}")
    return report
