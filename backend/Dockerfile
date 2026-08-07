# Bio-Motion Evaluator — API FastAPI + MediaPipe
FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/workspace/backend

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace/backend

COPY backend/requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt \
    && pip install --no-cache-dir "git+https://github.com/ultralytics/CLIP.git"

COPY backend/ .
# Videos gold standard: Settings.repo_root()/tests/assets/videos
COPY tests /workspace/tests

RUN sed -i 's/\r$//' /workspace/backend/docker/entrypoint.sh \
    && chmod +x /workspace/backend/docker/entrypoint.sh \
    && mkdir -p /workspace/backend/models /workspace/backend/data/downloads

EXPOSE 8000

ENTRYPOINT ["/workspace/backend/docker/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
