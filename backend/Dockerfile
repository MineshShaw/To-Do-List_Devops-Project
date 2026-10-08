FROM python:3.11-slim@sha256:f7d23353e1b15400d22ebe31189f4d314b87a4c129cc400c8c2d8d4ca127bf81

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade \
    pip==26.2.1 \
    setuptools==84.0.0 \
    wheel==0.48.0 \
    jaraco.context==6.1.2
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
