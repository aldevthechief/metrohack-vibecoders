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

После запуска основного `docker compose` эмулятор сам отправляет пакеты в бэк. Откройте дашборд и выберите **«Эмулятор NDTP»** — четыре ТС появятся на карте. Никакие HTTP-запросы для подключения делать не нужно.

Для своего источника отправляйте **бинарный NDTP по TCP на порт 9201** машины с Docker. В дашборде выбирается тот же режим. Если ТС не появились, откройте [состояние приёмника](http://localhost:8000/api/v1/ndtp/status): счётчик `received_packets` должен расти, `rejected_frames` — оставаться нулевым.

План остановок в репозитории относится к январю 2026 года. Поэтому текущий поток эмулятора показывает GPS без прогнозов. Чтобы проверить прогнозы и алерты без подготовки нового расписания, переключитесь на **«Тестовые данные»**: там 151 точка проходит через бэк и ML. Для прогноза на новых датах понадобятся актуальный план и соответствие устройств рейсам.

## Где смотреть результат

На **«Карте»** — ТС и карточка «Рейс под контролем»; в **«Прогнозах»** — алерты и фильтр высокого риска; в **«Динамике»** — общая сводка и GPS по ТС. [Метрики и замер скорости](PERFORMANCE.md), [полный JSON метрик](ml_service/research/vovchik/results/metrics.json).
