# Multi-stage Dockerfile for Railway deployment
# Optimized for Python + Node.js app with ML models

FROM python:3.9-slim as backend-builder

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy backend requirements
COPY backend/requirements.txt backend/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r backend/requirements.txt

# Frontend build stage
FROM node:18-alpine as frontend-builder

WORKDIR /app/frontend

# Copy frontend files
COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# Final stage
FROM python:3.9-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Python packages from builder
COPY --from=backend-builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY --from=backend-builder /usr/local/bin /usr/local/bin

# Copy built frontend
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# Copy backend code
COPY backend/ /app/backend/

# Copy configuration files
COPY railway.toml Procfile nixpacks.toml ./

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PORT=8000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Start command
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

