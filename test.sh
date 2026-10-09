#!/bin/bash
set -e

# Navigate to backend directory
cd "$(dirname "$0")/backend"

# Run pytest with coverage
PYTHONPATH="$PWD" DATABASE_URL="sqlite:///:memory:" TASK_API_KEY="test-api-key" python -m pytest -v --cov=app --cov-report=term-missing

echo "All tests passed successfully!"
