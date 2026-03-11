FROM python:3.11-slim AS base
WORKDIR /opt/l2

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir . && pip install --no-cache-dir uvicorn[standard]

COPY . .

RUN adduser --disabled-password --gecos "" l2user
USER l2user

EXPOSE 8002
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8002", "--workers", "1"]
