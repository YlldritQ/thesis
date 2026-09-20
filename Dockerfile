# syntax=docker/dockerfile:1.6
# -------------------------------------------------------------- builder
FROM python:3.11-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Build deps for any wheels that need compilation (numpy/pandas/sklearn).
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        build-essential gcc git curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY uv.lock ./
COPY requirements.txt ./
COPY requirements-lock.txt ./
COPY src ./src
COPY README.md ./
RUN pip install --no-cache-dir uv==0.11.28 \
 && uv sync --frozen --no-dev --extra notebooks --python /usr/local/bin/python

# -------------------------------------------------------------- runtime
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    THESIS_LOG_FORMAT=json \
    THESIS_DATA_DIR=/data \
    PATH="/app/.venv/bin:$PATH"

# Non-root user
RUN useradd --uid 10001 --shell /bin/bash --create-home thesis

# Copy the exact uv-lock-resolved environment from the builder. Keeping the
# same absolute path preserves virtualenv entry-point shebangs.
COPY --from=builder /app/.venv /app/.venv

# Copy application code (Streamlit, Airflow DAG, docs, tests)
WORKDIR /app
COPY src/thesis ./src/thesis
COPY streamlit_app ./streamlit_app
COPY airflow_dags ./airflow_dags
COPY docs ./docs
COPY README.md ./
COPY pyproject.toml ./
COPY uv.lock ./
COPY requirements.txt ./
COPY requirements-lock.txt ./

# Persistent data layer is a volume
RUN mkdir -p /data && chown -R thesis:thesis /data /app
USER thesis

# Default — launch the Streamlit dashboard on 0.0.0.0:8501
EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health', timeout=4).read()" || exit 1

CMD ["python", "-m", "streamlit", "run", "streamlit_app/Home.py", \
     "--server.address", "0.0.0.0", \
     "--server.port", "8501", \
     "--server.headless", "true"]
