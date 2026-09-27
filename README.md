# Metrohack — прогноз задержек транспорта

Бэк принимает NDTP или историческую телеметрию, ML-сервис рассчитывает задержку и риск, фронт показывает ТС, прогнозы и сводку.

- [Инструкция для жюри: запуск и проверка](JURY_GUIDE.md)
- [Производительность и дополнительные возможности](PERFORMANCE.md)
- [Обучение моделей и ограничения метрик](ml_service/research/vovchik/ML_RISK.md)
- [Конкурсный файл](submission.csv)

## Быстрый запуск

Если есть `ndtp-telemetry-emulator.tar` от организаторов:

```powershell
docker load -i .\ndtp-telemetry-emulator.tar
docker compose up --build -d
```

Без архива:

```powershell
docker compose -f compose.history.yaml up --build -d
```

Открыть **http://localhost:8080**. API — **http://localhost:8000/docs**, вход NDTP — TCP **9201**. Архив эмулятора не хранится в Git. Исторический режим доступен без него; внешний NDTP можно подать на порт 9201.

## Что где лежит

- `backend/` — NDTP TCP, REST API и исторический прогон.
- `ml_service/app/` — инференс и модели для Docker; `ml_service/research/` — ноутбуки, результаты и тесты.
- `frontend/` — карта и дашборд; `dataset/` — train/test/validate и формат входных CSV.

В текущем комплекте план остановок относится к **6–7 января 2026 года**. Для прогноза на новом живом потоке нужен актуальный план, связь `unit_id → tr_id` и текущее отклонение. Без них GPS виден, а прогноз не создаётся. Как подать эти данные, указано в инструкции для жюри.
