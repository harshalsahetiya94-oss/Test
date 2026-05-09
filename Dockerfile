FROM python:3.12-slim-bookworm

WORKDIR /app

# System deps for pdf parsing / pandas
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      build-essential libffi-dev curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY src/ ./src/
COPY templates/ ./templates/
COPY static/ ./static/

# Persistent data lives under /data (Fly volume mounted here).
# /app/output and /app/input are symlinked to /data so existing code Just Works.
RUN mkdir -p /data/output /data/input \
 && rm -rf /app/output /app/input \
 && ln -s /data/output /app/output \
 && ln -s /data/input /app/input

ENV PYTHONUNBUFFERED=1 \
    PORT=8080 \
    FLASK_ENV=production

EXPOSE 8080

# Run the Flask app via gunicorn. src.app exposes `app`.
CMD ["sh", "-c", "exec gunicorn -w 2 -b 0.0.0.0:${PORT:-8080} --timeout 120 src.app:app"]
