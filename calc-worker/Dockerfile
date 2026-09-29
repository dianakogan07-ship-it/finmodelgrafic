# Ubuntu 24.04 + ICU 74 — окружение, на котором проверена сверка Aspose с Excel (backend/tests/golden).
# libfontconfig1 нужен SkiaSharp внутри Aspose, без него процесс падает при загрузке книги.
FROM ubuntu:24.04
RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 python3-venv libicu74 libfontconfig1 ca-certificates \
 && rm -rf /var/lib/apt/lists/*
RUN python3 -m venv /venv
ENV PATH=/venv/bin:$PATH
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY engine.py app.py spike.py ./
ENV MODEL_DIR=/data/models
EXPOSE 8001
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]
