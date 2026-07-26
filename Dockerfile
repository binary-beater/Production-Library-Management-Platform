FROM python:3.11-slim

WORKDIR /app

# Create a non-root system group and user
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -d /app -s /sbin/nologin -c "Non-root Application User" appuser

# Install system dependencies required for MySQL client
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    default-libmysqlclient-dev \
    pkg-config \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy configuration files and app source code first to allow dependency installation
COPY --chown=appuser:appgroup pyproject.toml .
COPY --chown=appuser:appgroup README.md .
COPY --chown=appuser:appgroup app app

RUN pip install --no-cache-dir .

# Copy remaining layers
COPY --chown=appuser:appgroup tests tests
COPY --chown=appuser:appgroup docs docs

# Change owner of all files in app to the non-root user
RUN chown -R appuser:appgroup /app

# Switch to the non-root user context
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
