FROM python:3.11-slim

WORKDIR /app

RUN adduser --disabled-password --gecos '' --uid 1001 appuser

COPY requirements.txt .

# 1. Upgrade core tools
# 2. Install requirements
# 3. Purge the ensurepip bundled wheels to stop Trivy from scanning inert files
RUN pip install --no-cache-dir --upgrade \
    "pip>=26.2.1" \
    "setuptools>=78.1.1" \
    "wheel>=0.48.0" \
    "jaraco.context>=6.1.2" && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir --upgrade \
    "msgpack>=1.2.1" \
    "urllib3>=2.8.0" && \
    pip uninstall --yes pip setuptools wheel && \
    rm -rf /usr/local/lib/python3.11/ensurepip/_bundled/

COPY --chown=appuser:appuser . .

USER appuser

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]