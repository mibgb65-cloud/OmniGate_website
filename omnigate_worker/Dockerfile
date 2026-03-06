FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV DEBIAN_FRONTEND=noninteractive
ENV BROWSER_HEADLESS=true
ENV BROWSER_SANDBOX=false
ENV BROWSER_ARGS=--disable-dev-shm-usage,--no-first-run,--disable-gpu,--disable-software-rasterizer

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        chromium \
        fonts-liberation \
        tzdata \
    && ln -sf /usr/bin/chromium /usr/bin/chromium-browser \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY src ./src

CMD ["python", "-m", "src.main"]
