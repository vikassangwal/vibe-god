# Multi-stage Dockerfile for Vibe-God Enterprise
# Stage 1: Build dependencies
FROM python:3.11-slim AS builder

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
ENV POETRY_VERSION=1.8.2
RUN pip install --no-cache-dir poetry==$POETRY_VERSION

# Configure Poetry
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VENV_IN_PROJECT=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

WORKDIR /app

# Copy Poetry files
COPY pyproject.toml poetry.lock* ./

# Install dependencies
RUN poetry install --only=main --no-root && rm -rf $POETRY_CACHE_DIR

# Stage 2: Runtime
FROM python:3.11-slim AS runtime

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    tesseract-ocr \
    tesseract-ocr-hin \
    tesseract-ocr-eng \
    poppler-utils \
    ffmpeg \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r wifegod && useradd -r -g wifegod -d /app -s /bin/bash wifegod

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv .venv

# Copy application code
COPY --chown=wifegod:wifegod python/ ./python/
COPY --chown=wifegod:wifegod config/ ./config/
COPY --chown=wifegod:wifegod scripts/ ./scripts/

# Make scripts executable
RUN chmod +x scripts/*.sh

# Set PATH to use venv
ENV PATH="/app/.venv/bin:$PATH"

# Create directories
RUN mkdir -p /app/data /app/logs /app/temp /app/models && \
    chown -R wifegod:wifegod /app

# Switch to non-root user
USER wifegod

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose ports
EXPOSE 8000 8001

# Default command
CMD ["python", "-m", "python.apps.api.main"]