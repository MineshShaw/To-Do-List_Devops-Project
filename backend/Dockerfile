FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel "jaraco.context>=6.1.0"
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY . .

# Create dedicated non-root user
RUN adduser --disabled-password --gecos '' --uid 1001 appuser && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Run Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
