# ==========================================
# Multi-Stage Production-Grade Dockerfile
# ==========================================

# --- Stage 1: Build & Dependencies ---
FROM python:3.11-slim AS builder

WORKDIR /app

# Install compilation tools for potential packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency specifications
COPY requirements.txt pyproject.toml ./

# Install packages into local user directory to reduce final image size
RUN pip install --no-cache-dir --user -r requirements.txt


# --- Stage 2: Final Runtime ---
FROM python:3.11-slim AS runner

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/root/.local/bin:$PATH

# Copy installed libraries from builder stage
COPY --from=builder /root/.local /root/.local

# Copy application source code
COPY . .

# Expose FastAPI (8000) and Streamlit (8501) ports
EXPOSE 8000
EXPOSE 8501

# Default runtime command (starts the FastAPI production Uvicorn server)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
