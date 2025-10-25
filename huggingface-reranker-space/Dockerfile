FROM python:3.10-slim

WORKDIR /app

# Create cache directory for HuggingFace
RUN mkdir -p /app/.cache && chmod 777 /app/.cache

# Set environment variables
ENV TRANSFORMERS_CACHE=/app/.cache
ENV HF_HOME=/app/.cache
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies with proper versions
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app.py .

# Expose port
EXPOSE 7860

# Run application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]

