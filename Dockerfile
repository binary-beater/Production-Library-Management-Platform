FROM python:3.11-slim

WORKDIR /app

# Install system dependencies required for MySQL client
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    default-libmysqlclient-dev \
    pkg-config \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy configuration files first to maximize Docker layer caching
COPY pyproject.toml .
COPY README.md .

RUN pip install --no-cache-dir -e .

# Copy application layers
COPY app app
COPY tests tests
COPY docs docs

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
