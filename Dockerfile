FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends build-essential gcc git curl gosu && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN useradd -m -u 1000 appuser && mkdir -p /app/data /app/logs /app/output /app/sandbox /app/cache /app/data/backups && chown -R appuser:appuser /app

COPY --chown=appuser:appuser . .

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 CMD python -c "import requests; requests.get('http://localhost:8080/health', timeout=5)" || exit 1

ENTRYPOINT ["/bin/bash", "-c", "mkdir -p /app/data /app/logs /app/output /app/sandbox /app/cache /app/data/backups && chown -R appuser:appuser /app/data /app/logs /app/output /app/sandbox /app/cache /app/data/backups 2>/dev/null || true; exec gosu appuser python -u main.py webhook"]