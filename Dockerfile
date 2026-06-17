FROM python:3.11-slim AS base

WORKDIR /app

# System dependencies for WeasyPrint (pango/cairo PDF rendering)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-xlib-2.0-0 \
    libffi-dev \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Install store universe package first (changes less often)
COPY packages/cinderhaven-store-universe/ /app/packages/cinderhaven-store-universe/
RUN pip install --no-cache-dir /app/packages/cinderhaven-store-universe/

# Install app dependencies
COPY pyproject.toml /app/
RUN pip install --no-cache-dir ".[pdf]"

# Copy application code
COPY app/ /app/app/
COPY assets/ /app/assets/
COPY wsgi.py /app/

# Pre-build parquet cache so cold starts don't block port binding
RUN python -c "from app.data import SCAN_QUARTERLY, LAST_SCAN; print(f'Cache built: {len(SCAN_QUARTERLY)} quarterly rows, {len(LAST_SCAN)} last-scan rows')"

EXPOSE 8050

CMD ["gunicorn", "wsgi:server", "--bind", "0.0.0.0:8050", "--workers", "1", "--worker-class", "gthread", "--threads", "2", "--timeout", "120", "--preload"]
