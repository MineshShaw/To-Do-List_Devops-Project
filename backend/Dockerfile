FROM python:3.11-slim

WORKDIR /app

# 1. Create dedicated non-root user early (better for Docker caching)
RUN adduser --disabled-password --gecos '' --uid 1001 appuser

# 2. Install dependencies & patch Trivy vulnerabilities
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade \
    pip \
    setuptools>=84.0.0 \
    wheel>=0.48.0 \
    jaraco.context>=6.1.2 \
    msgpack>=1.2.1 \
    urllib3>=2.8.0
    
RUN pip install --no-cache-dir -r requirements.txt

# 3. Copy backend source code directly to the non-root user
# (This prevents Docker from creating a duplicate layer just for permission changes)
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Run Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]