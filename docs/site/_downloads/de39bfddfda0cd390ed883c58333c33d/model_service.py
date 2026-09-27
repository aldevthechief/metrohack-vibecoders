from pathlib import Path

import pandas as pd
from .ml_risk import load_models, predict_for_frontend


WINDOWS = ["30s", "1m", "3m", "5m", "10m", "15m"]

SCHEDULE = [
    "tr_id",
    "target_stop_id",
    "hour",
    "minute",
    "minute_of_day",
    "day_of_week",
    "is_weekend",
    "sin_time",
    "cos_time",
    "target_hour",
    "target_minute_of_day",
    "forecast_horizon_s",
    "cur_dev_s",
    "abs_cur_dev",
    "is_late_now",
    "is_early_now",
    "stops_to_target",
]

SPATIAL = [
    "sp_has_position",
    "sp_position_age_s",
    "sp_distance_to_target_m",
    "sp_approach_1m_m",
    "sp_approach_speed_1m_mps",
    "sp_approach_3m_m",
    "sp_approach_speed_3m_mps",
]

TELEMETRY = [
    "unit_id",
    "event_time",
    "receive_time",
    "gps_time",
    "speed_now",
    "telemetry_age",
    "gps_age",
    "receive_delay",
    "last_packet_is_hist",
    "packet_count_15m",
    "packet_frequency",
    "hist_packet_fraction",
    "mean_receive_delay",
    "max_packet_gap",
]

TELEMETRY += [
    f"speed_{stat}_{window}"
    for window in WINDOWS
    for stat in ("mean", "std", "min", "max", "median")
]

TELEMETRY += [
    "stopped_fraction_1m",
    "stopped_fraction_3m",
    "stopped_fraction_5m",
    "speed_slope_1m",
    "speed_slope_3m",
    "speed_slope_5m",
    "longest_stop_5m",
    "stop_count_10m",
    "time_since_last_move",
    "current_stop_duration",
]

FEATURE_COLS = SCHEDULE + SPATIAL + TELEMETRY

CATEGORICAL = [
    "tr_id",
    "target_stop_id",
    "unit_id",
]


class ModelService:
    def __init__(self) -> None:
        model_path = (
            Path(__file__).resolve().parent.parent
            / "artifacts"
            / "final_model.cbm"
        )

        self._model, self._risk_model, self._risk_metadata = load_models(
            model_path.parent, model_path
        )

    def predict(
        self,
        features: dict[str, float | int | str | None],
    ) -> float:
        return self.predict_details(features)["predicted_delay_s"]

    def predict_details(
        self,
        features: dict[str, float | int | str | None],
    ) -> dict:
        frame = pd.DataFrame(
            [features],
        )

        # Гарантируем те же колонки и тот же порядок,
        # что использовались при обучении.
        for column in FEATURE_COLS:
            if column not in frame.columns:
                frame[column] = None

        frame = frame[FEATURE_COLS].copy()

        # Полностью повторяем model_input()
        # из unified.ipynb.
        for column in CATEGORICAL:
            frame[column] = (
                frame[column]
                .fillna("missing")
                .astype(str)
            )

        frame["sample_id"] = "live"
        result = predict_for_frontend(
            self._model, self._risk_model, self._risk_metadata, frame
        )[0]
        return {
            "predicted_delay_s": result["predicted_delay_s"],
            "delay_probability": result["delayProbability"],
            "delay_threshold_sec": result["delayThresholdSec"],
            "probability_method": result["probabilityMethod"],
            "reason_factors": result["explanation"]["factors"],
        }
