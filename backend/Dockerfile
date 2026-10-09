FROM python:3.11-alpine

WORKDIR /app

# Install system dependencies needed for psycopg2-binary and build
RUN apk add --no-cache --virtual .build-deps gcc musl-dev postgresql-dev && \
    apk add --no-cache libpq

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Remove build dependencies
RUN apk del .build-deps

# Copy backend source code
COPY . .

# Create dedicated non-root user
RUN adduser --disabled-password --gecos '' --uid 1001 appuser && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Run Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
