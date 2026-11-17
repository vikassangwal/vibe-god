# Wife God - Dockerfile for Containerized Deployment
# Multi-stage build for smaller final image

# ============================================
# Stage 1: Build dependencies
# ============================================
FROM python:3.11-slim AS builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgtk-3-0 \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libv4l-dev \
    libxvidcore-dev \
    libx264-dev \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libdc1394-22-dev \
    tesseract-ocr \
    tesseract-ocr-hin \
    libtesseract-dev \
    portaudio19-dev \
    python3-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install build dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright and browsers
RUN pip install --no-cache-dir playwright
RUN playwright install-deps chromium
RUN playwright install chromium

# ============================================
# Stage 2: Runtime image
# ============================================
FROM python:3.11-slim AS runtime

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgtk-3-0 \
    libavcodec58 \
    libavformat58 \
    libswscale5 \
    libv4l-0 \
    libxvidcore4 \
    libx264-164 \
    libjpeg62-turbo \
    libpng16-16 \
    libtiff5 \
    libdc1394-22 \
    tesseract-ocr \
    tesseract-ocr-hin \
    libtesseract4 \
    portaudio19-dev \
    chromium \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY . .

# Create required directories
RUN mkdir -p /app/data /app/input_documents /app/output /app/temp /app/models /app/logs /app/data_products

# Create non-root user for security
RUN groupadd -r wifegod && useradd -r -g wifegod wifegod
RUN chown -R wifegod:wifegod /app
USER wifegod

# Expose ports (for webhook server if needed)
EXPOSE 8080 8083

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    OLLAMA_URL=http://host.docker.internal:11434

# Default command
ENTRYPOINT ["python", "-m", "main"]
CMD ["--interactive"]