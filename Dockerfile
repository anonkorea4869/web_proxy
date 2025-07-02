FROM python:3.9-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Final stage
FROM python:3.9-slim

# Install MySQL client and curl
RUN apt-get update && apt-get install -y --no-install-recommends \
    default-libmysqlclient-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /project

# Copy Python packages and application code
COPY --from=builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY --from=builder /usr/local/bin/uvicorn /usr/local/bin/
COPY project/ /project/

RUN mkdir -p /project/data && \
    chown -R appuser:appuser /project

ENV PYTHONPATH=/project \
    PYTHONUNBUFFERED=1 \
    ADMIN_USERNAME=admin \
    ADMIN_PASSWORD=admin \
    MYSQL_HOST=mysql \
    MYSQL_PORT=3306 \
    MYSQL_USER=anonkorea4869 \
    MYSQL_PASSWORD=anonkorea4869 \
    MYSQL_DATABASE=proxy

USER appuser

EXPOSE 8080 8000

HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["sh", "-c", "cd /project/proxy && python main.py & cd /project/web && python main.py & wait"]
