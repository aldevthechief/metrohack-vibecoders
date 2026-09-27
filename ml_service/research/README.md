# Исследования моделей

## Основной путь для сдачи

- `vovchik/unified.ipynb` — воспроизводимое обучение регрессора задержки и классификатора риска, формирование вероятности, SHAP и `submission.csv`.
- `vovchik/train_from_notebook.py` — запуск его кодовых ячеек из корня репозитория без Jupyter-сервера.
- `vovchik/results/` — обученные модели, метрики, прогнозы и конкурсный CSV.
- `../app/artifacts/` — проверенные копии моделей, которые загружает ML-сервис в Docker.
- `vovchik/tests/` — проверки временных границ признаков, риска, SHAP и формата submission.

Команда переобучения из корня репозитория:

```bash
python ml_service/research/vovchik/train_from_notebook.py
```

После обучения сравните модели и скопируйте `final_model.cbm`, `risk_model.cbm`, `risk_metadata.json` из `vovchik/results/` в `ml_service/app/artifacts/`, затем пересоберите ML-сервис. Полный конкурсный файл лежит в корне репозитория как `submission.csv`. Метрики и ограничения проверки описаны в [ML_RISK.md](vovchik/ML_RISK.md).

## Остальные notebooks

- `vovchik/baseline_regressor.ipynb` — первоначальный notebook только с регрессором; хранится для истории эксперимента.
- `vovchik/Spatial_Route_Progress-Copy2.ipynb` — исследование пространственных признаков.
- `mishgan/metr0-hack-mishgan.ipynb` — альтернативное исследование признаков. Его схема не используется в текущем API инференса.
