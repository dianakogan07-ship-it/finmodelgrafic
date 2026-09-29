FROM python:3.11-slim-bookworm
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY backend/seeds ./seeds
COPY config /config
ENV CELL_MAP=/config/cell_map.yaml MODEL_DIR=/data/models SEED_MODEL=/data/model.xlsx
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
