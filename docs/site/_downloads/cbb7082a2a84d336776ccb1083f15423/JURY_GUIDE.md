# Как проверить решение

## Запуск

Из корня репозитория с архивом эмулятора:

```powershell
docker load -i .\ndtp-telemetry-emulator.tar
docker compose up --build -d
```

Без архива, для исторического режима и внешнего NDTP:

```powershell
docker compose -f compose.history.yaml up --build -d
```

Архив эмулятора в Git не входит. Дашборд: **http://localhost:8080**, API: **http://localhost:8000/docs**.

## Исторический датасет

На стартовом экране выберите **«Тестовые данные»**. Бэк читает комплект `dataset/validate` и рассчитывает 151 прогноз через ML-сервис; сохранённые ответы в дашборд не подставляются. Ход прогона: `GET /api/v1/replay`. Карта запускается сама на ×0,25.

Свой набор подайте в формате `validate/points.csv`, `validate/traffic.csv`, `validate/schedule_plan.csv`. Положите их в `input/` и добавьте к Compose файл `compose.input.yaml`:

```yaml
services:
  backend:
    environment:
      REPLAY_POINTS_PATH: /input/points.csv
      REPLAY_TRAFFIC_PATH: /input/traffic.csv
      SCHEDULE_PLAN_PATH: /input/schedule_plan.csv
    volumes:
      - ./input:/input:ro
```

Запуск: `docker compose -f compose.history.yaml -f compose.input.yaml up --build -d`. После запуска выберите «Тестовые данные».

## Поток NDTP

С образом эмулятора четыре устройства начинают отправлять бинарные пакеты на TCP-порт **9201**. Внешний источник подключается к тому же порту. На стартовом экране выберите **«Эмулятор NDTP»**. Приём пакетов проверьте через `GET /api/v1/ndtp/status`, позиции всех ТС — через `GET /api/v1/fleet`.

Для живого прогноза дополнительно нужны соответствие `unit_id → tr_id`, актуальный план остановок и текущее отклонение. Их можно передать через `NDTP_TRAFFIC_PATH` / `SCHEDULE_PLAN_PATH` и API `/api/v1/ndtp/units`, `/api/v1/schedule`, `/api/v1/current-deviation`. План в репозитории относится к январю 2026 года: нынешний поток эмулятора без нового плана показывает GPS, но не прогноз.

## Где смотреть результат

На **«Карте»** — ТС и карточка «Рейс под контролем»; в **«Прогнозах»** — список и фильтр высокого риска; в **«Динамике»** — общая сводка и GPS по ТС. Живые прогнозы и инциденты также доступны через `GET /api/dashboard` и `GET /api/v1/incidents`. [Метрики и замер скорости](PERFORMANCE.md), [полный JSON метрик](ml_service/research/vovchik/results/metrics.json).
