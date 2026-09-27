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

Для своего источника отправляйте **бинарный NDTP 6.2 по TCP на `<адрес Docker-хоста>:9201`**. Это не HTTP и не JSON. Для каждого `unitId` сначала нужен handshake (`serviceId=0`, `type=100`), затем realtime-пакеты (`serviceId=1`, `type=101`) с `G6CellNav00` первой ячейкой. Приёмник проверяет сигнатуру `0x7E7E` и CRC-16/Modbus; из навигационной ячейки читает время, координаты, скорость и курс. Остальные ячейки не мешают приёму, но сейчас не идут в признаки модели. [Полный формат кадра](dataset/docs/Emulator-and-Telematic-Packets-Specification.md). В дашборде выберите тот же режим **«Эмулятор NDTP»**.

HTTP-адреса для настройки и проверки результата:

| Метод и адрес | Что смотреть |
|---|---|
| `GET/POST http://localhost:18080/api/config` | Конфиг эмулятора. При обычном `docker compose` бэк задаёт его сам; вручную вызывать не нужно. |
| `GET http://localhost:8000/api/v1/ndtp/status` | JSON: `received_packets` растёт, `rejected_frames` и `processing_errors` остаются `0`. |
| `GET http://localhost:8000/api/v1/fleet` | Последние GPS-точки, в том числе для ТС без прогноза. |
| `GET http://localhost:8000/api/dashboard` | Живые прогнозы, когда есть данные расписания. |

Если устройство надо связать с рейсом, подайте `traffic.csv` через `NDTP_TRAFFIC_PATH` в формате `unit_id,tr_id,event_time` (например, `123,456,2026-01-06 12:30:00`) или вызовите `POST http://localhost:8000/api/v1/ndtp/units` с JSON `{"unit_id":123,"tr_id":"456"}`. CSV нужно примонтировать в контейнер бэка, как показано выше для папки `input/`.

План остановок в репозитории относится к январю 2026 года. Поэтому текущий поток эмулятора показывает GPS без прогнозов. Чтобы проверить прогнозы и алерты без подготовки нового расписания, переключитесь на **«Тестовые данные»**: там 151 точка проходит через бэк и ML. Для живого прогноза на новых датах нужен актуальный план (`SCHEDULE_PLAN_PATH` или `POST /api/v1/schedule`) и текущее отклонение (`POST /api/v1/current-deviation`).

## Где смотреть результат

На **«Карте»** — ТС и карточка «Рейс под контролем»; в **«Прогнозах»** — алерты и фильтр высокого риска; в **«Динамике»** — общая сводка и GPS по ТС. [Метрики и замер скорости](PERFORMANCE.md), [полный JSON метрик](ml_service/research/vovchik/results/metrics.json).
