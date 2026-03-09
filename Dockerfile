FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app/backend

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    shared-mime-info \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz0b \
    libharfbuzz-subset0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    libffi8 \
    libjpeg62-turbo \
    zlib1g \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip && pip install -r /tmp/requirements.txt

COPY backend /app/backend
COPY scripts /app/scripts

RUN useradd --create-home --shell /bin/bash appuser \
    && chmod +x /app/scripts/deploy.sh \
    && mkdir -p /app/backend/staticfiles /app/backend/media /app/backend/logs \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 CMD python -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8000/health/", timeout=4)'

CMD /app/scripts/deploy.sh gunicorn --bind 0.0.0.0:${PORT:-8000} config.wsgi:application
CMD ["/app/scripts/deploy.sh"]
