# Build from the repository root:
#   docker build -f deploy/Dockerfile -t smart-businesswriter .
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    BP_STATE_DIR=/data/state \
    BP_CASES_DIR=/data/cases \
    BP_INTAKE_DIR=/data/intake

WORKDIR /app
COPY . /app

RUN useradd --create-home --uid 10001 bp \
    && mkdir -p /data/state /data/cases /data/intake \
    && chown -R bp:bp /data /app
USER bp

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4)"

CMD ["python", "scripts/serve.py", "--host", "0.0.0.0", "--port", "8000"]
