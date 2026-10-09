#!/bin/bash
set -e

# Navigate to project root
cd "$(dirname "$0")"

read -p "Press Enter to continue..."

echo "=== Running pytest -v ==="
cd backend
PYTHONPATH=$PWD DATABASE_URL=sqlite:///:memory: python -m pytest -v
cd ..
read -p "Press Enter to continue..."

echo "=== Building and starting containers ==="
docker compose build
docker compose up -d
docker ps
read -p "Press Enter to continue..."

echo "=== Helm list ==="
helm list -n todo-app
read -p "Press Enter to continue..."

echo "=== kubectl get pods ==="
kubectl get pods -n todo-app
read -p "Press Enter to continue..."

echo "=== kubectl get svc ==="
kubectl get svc -n todo-app
read -p "Press Enter to continue..."

echo "=== curl metrics endpoint ==="
curl -s http://localhost:8000/metrics | head -n 20
read -p "Press Enter to continue..."
