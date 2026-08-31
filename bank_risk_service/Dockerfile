# Use official Python 3.11 slim image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONUTF8=1 \
    PYTHONPATH="/app"

WORKDIR /app

# Install system build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy bank_risk_service self-contained source code & calculation engine
COPY . /app/bank_risk_service/

# Expose port 8080
EXPOSE 8080

# Run FastAPI with uvicorn
CMD ["python", "-m", "uvicorn", "bank_risk_service.main:app", "--host", "0.0.0.0", "--port", "8080"]
