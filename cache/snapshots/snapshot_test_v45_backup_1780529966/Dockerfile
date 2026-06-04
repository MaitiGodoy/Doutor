# ============================================================
# Doutor v4.1 — Multi-stage Production Build
# ============================================================
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ============================================================
FROM python:3.11-slim AS runtime

RUN useradd -m -u 1000 appuser \
    && mkdir -p /app/data /app/logs /app/output /app/sandbox /app/cache \
    && chown -R appuser:appuser /app

WORKDIR /app

COPY --from=builder /root/.local /home/appuser/.local
ENV PATH=/home/appuser/.local/bin:$PATH

COPY --chown=appuser:appuser . .

USER appuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health', timeout=5)"

EXPOSE 8080

VOLUME ["/app/data", "/app/logs", "/app/cache"]

ENTRYPOINT ["python", "main.py"]
CMD ["webhook", "8080"]
