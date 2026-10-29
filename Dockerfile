FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency specifications
COPY requirements.txt requirements-ml.txt ./

# Install python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code, models, and data
COPY app/ app/
COPY data/ data/
COPY models/ models/
COPY pyproject.toml .env.example README.md ./

# Set environment variables for global production hosting
ENV PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    DATABASE_URL=sqlite:///./linkintel.db \
    ENABLE_SPAM_MODEL=true \
    SPAM_MODEL_PATH=models/spam_risk.joblib

# Expose FastAPI port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Launch uvicorn bound to 0.0.0.0 for global internet access
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
