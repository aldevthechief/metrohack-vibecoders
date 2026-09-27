FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY dataset/validate/schedule_plan.csv ./schedule_plan.csv
COPY backend/config/ndtp_units.csv ./ndtp_units.csv
COPY frontend/src/data/demo.json ./replay/demo.json
ENV DASHBOARD_REPLAY_PATH=/app/replay/demo.json
ENV SCHEDULE_PLAN_PATH=/app/schedule_plan.csv
ENV NDTP_UNITS_PATH=/app/ndtp_units.csv
EXPOSE 8000 9201
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
