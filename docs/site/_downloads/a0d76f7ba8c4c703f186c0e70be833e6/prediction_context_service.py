from datetime import datetime

from app.models.schedule import PredictionContext


class PredictionContextService:
    def __init__(self) -> None:
        self._contexts: dict[str, PredictionContext] = {}
        self._current_deviations: dict[str, float] = {}
        self._deviation_sources: dict[str, str] = {}
        self._deviation_observed_at: dict[str, datetime] = {}

    def set(self, context: PredictionContext) -> None:
        self._contexts[context.tr_id] = context
        self.set_current_deviation(context.tr_id, context.cur_dev_s, source="provided")

    def update_context(self, context: PredictionContext) -> None:
        self._contexts[context.tr_id] = context

    def set_current_deviation(
        self,
        tr_id: str,
        cur_dev_s: float,
        source: str = "provided",
        observed_at: datetime | None = None,
    ) -> bool:
        previous_time = self._deviation_observed_at.get(tr_id)
        if observed_at is not None and previous_time is not None and observed_at <= previous_time:
            return False
        self._current_deviations[tr_id] = cur_dev_s
        self._deviation_sources[tr_id] = source
        if observed_at is None:
            self._deviation_observed_at.pop(tr_id, None)
        else:
            self._deviation_observed_at[tr_id] = observed_at
        return True

    def get_current_deviation(self, tr_id: str) -> float | None:
        return self._current_deviations.get(tr_id)

    def get_current_deviation_source(self, tr_id: str) -> str | None:
        return self._deviation_sources.get(tr_id)

    def get(self, tr_id: str) -> PredictionContext | None:
        return self._contexts.get(tr_id)

    def remove(self, tr_id: str) -> None:
        self._contexts.pop(tr_id, None)
        self._current_deviations.pop(tr_id, None)
        self._deviation_sources.pop(tr_id, None)
        self._deviation_observed_at.pop(tr_id, None)

    def get_all(self) -> list[PredictionContext]:
        return list(self._contexts.values())
