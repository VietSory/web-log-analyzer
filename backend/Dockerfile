FROM python:3.12.13-slim-bookworm@sha256:d50fb7611f86d04a3b0471b46d7557818d88983fc3136726336b2a4c657aa30b

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app

COPY requirements.txt ./requirements.txt
RUN python -m pip install -r requirements.txt

COPY --chown=app:app . .
RUN mkdir -p /data/uploads /data/models && chown -R app:app /data

USER app

ENV APP_HOST=0.0.0.0 \
    APP_PORT=8000 \
    APP_RELOAD=false \
    DATABASE_PATH=/data/weblog_analyzer.db \
    UPLOAD_DIR=/data/uploads \
    MODEL_DIR=/data/models

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=3).read()"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
