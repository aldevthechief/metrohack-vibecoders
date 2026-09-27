FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY dataset/validate/schedule_plan.csv ./schedule_plan.csv
COPY dataset/validate/points.csv ./replay_points.csv
COPY dataset/validate/traffic.csv ./replay_traffic.csv
COPY backend/config/ndtp_units.csv ./ndtp_units.csv
COPY backend/config/ndtp_emulator.json ./ndtp_emulator.json
ENV SCHEDULE_PLAN_PATH=/app/schedule_plan.csv
ENV REPLAY_POINTS_PATH=/app/replay_points.csv
ENV REPLAY_TRAFFIC_PATH=/app/replay_traffic.csv
ENV NDTP_UNITS_PATH=/app/ndtp_units.csv
ENV NDTP_EMULATOR_CONFIG_PATH=/app/ndtp_emulator.json
EXPOSE 8000 9201
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
