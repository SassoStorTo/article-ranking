FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:0.5.29 /uv /uvx /bin/

WORKDIR /workspace

COPY pyproject.toml uv.lock README.md ./
COPY news_ranker ./news_ranker
COPY livedemo/pyproject.toml livedemo/uv.lock livedemo/README.md ./livedemo/

WORKDIR /workspace/livedemo
RUN uv sync --no-dev

WORKDIR /workspace
COPY livedemo ./livedemo

ENV PATH="/workspace/livedemo/.venv/bin:${PATH}"
ENV PYTHONPATH="/workspace"

CMD ["uvicorn", "livedemo.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
