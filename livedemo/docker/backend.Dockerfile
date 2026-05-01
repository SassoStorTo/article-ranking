FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir uv && mkdir -p /var/livedemo

COPY livedemo/pyproject.toml livedemo/uv.lock* livedemo/README.md ./livedemo/
WORKDIR /app/livedemo
RUN uv sync --frozen --no-dev || uv sync --no-dev

COPY livedemo/app ./app

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
