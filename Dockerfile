# Reproducible test image for the design_to_reality monorepo.
# Build:  docker build -t dtr .
# Test:   docker run --rm dtr
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    MODEL_PROVIDER=fake \
    EMBEDDING_PROVIDER=fake

# Repo root as WORKDIR: tests resolve paths across both packages.
WORKDIR /app

# Pinned third-party deps first, so this layer caches across code changes.
COPY constraints.txt ./
RUN pip install -r constraints.txt

COPY . .
RUN pip install --no-deps -e "dataset_factory[dev]" -e "vision_engine[dev]"

CMD ["sh", "-c", "cd /app/dataset_factory && python -m pytest -q && cd /app/vision_engine && python -m pytest -q"]
