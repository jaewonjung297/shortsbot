# Alternative to GitHub Actions: run on any container scheduler (Cloud Run Jobs, Fly, ECS, a VPS cron).
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
      ffmpeg libcairo2-dev pkg-config gcc fonts-inter fonts-crosextra-caladea \
    && fc-cache -f && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Mount a volume at /data so history survives between runs.
ENV SHORTSBOT_HISTORY=/data/history.json
CMD ["python", "-m", "shortsbot", "run", "--out", "/data/latest"]
