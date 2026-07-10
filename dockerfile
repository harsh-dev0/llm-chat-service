FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt   # own layer: deps re-install only when this file changes

COPY app ./app

RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser                                          # never run as root

EXPOSE 8000

# 0.0.0.0, not 127.0.0.1 — localhost inside a container is unreachable from outside it
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]