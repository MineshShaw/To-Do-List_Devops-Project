# To-Do List DevOps Capstone Project

## Project Overview

This is a lightweight To-Do List web application built with FastAPI, SQLite/PostgreSQL, and a vanilla HTML/JS frontend. It is designed specifically as a target for a comprehensive DevOps CI/CD, Infrastructure as Code (IaC), and Kubernetes deployment pipeline. The project demonstrates containerization, automated testing, security scanning, cloud infrastructure provisioning, Kubernetes orchestration, and observability practices.

## Architecture & Technologies

The project utilizes a modern DevOps toolchain:

- **Backend**: Python, FastAPI, SQLAlchemy, Alembic
- **Frontend**: Vanilla HTML, JavaScript, CSS
- **Database**: PostgreSQL (production), SQLite (testing)
- **Testing**: Pytest
- **Containerization**: Docker, Docker Compose, Multi-stage builds
- **CI/CD**: GitHub Actions
- **Security Scanning**: Trivy
- **Container Registry**: GitHub Container Registry (GHCR)
- **Infrastructure as Code**: Terraform
- **Cloud Provider**: Amazon Web Services (AWS)
- **Kubernetes**: Amazon EKS
- **Package Management**: Helm
- **Monitoring**: Prometheus
- **Visualization**: Grafana

## Local Development Setup

To run the application locally using Docker Compose:

```bash
docker compose up --build
```

This will start the following services:
- **PostgreSQL** database on port `5432`
- **Backend** FastAPI application on port `8000`
- **Frontend** served on port `3000` via nginx

Open `http://localhost:3000` and add tasks directly. In Compose, the browser
calls the backend at `http://localhost:8000`; the backend API is also available
there directly. Tasks are written to the PostgreSQL `postgres_data` volume.

The frontend can be accessed at `http://localhost:3000`, and the backend API is available at `http://localhost:8000`.

## API & Authentication

The API uses JWT bearer authentication. Sign up once, then send the returned
token on every task request:

```bash
# 1. Create an account -> returns a JWT (201)
curl -X POST http://localhost:8000/signup \
     -H "Content-Type: application/json" \
     -d '{"username": "alice", "password": "secret123"}'

# 2. Or log in with the OAuth2 password flow -> returns a JWT
curl -X POST http://localhost:8000/login \
     -d "username=alice&password=secret123"

# 3. Call a protected endpoint with the token
curl http://localhost:8000/tasks \
     -H "Authorization: Bearer <ACCESS_TOKEN>"
```

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/health` | No | Liveness probe |
| `POST` | `/signup` | No | Register a user, returns a JWT |
| `POST` | `/login` | No | OAuth2 password flow, returns a JWT |
| `GET` | `/tasks?status=pending` | Yes | List **your** tasks, optional status filter (`pending`, `in-progress`, `done`) |
| `POST` | `/tasks` | Yes | Create a task owned by you |
| `GET` | `/tasks/{id}` | Yes | Fetch one of your tasks |
| `PUT` | `/tasks/{id}` | Yes | Update one of your tasks |
| `DELETE` | `/tasks/{id}` | Yes | Delete one of your tasks |

Tasks are scoped to their owner: any access to another user's task returns
`404 Not Found`. Invalid status values return `422 Unprocessable Entity`, and
missing/invalid tokens return `401 Unauthorized`.

### Database migrations

The schema is managed with Alembic. After changing the models, generate and
apply a migration:

```bash
cd backend
export DATABASE_URL="postgresql+psycopg2://postgres:postgres@localhost:5432/todo_db"
alembic revision --autogenerate -m "add users and task status/due_date/owner"
alembic upgrade head
```

## CI/CD Pipeline

The GitHub Actions workflow (`.github/workflows/ci-cd.yml`) automates the entire build and deployment pipeline:

1. **Testing**: Runs Pytest against the backend to validate functionality and ensure code quality. The build will fail if any tests do not pass.
2. **Backend Build, Scan, and Push**: Builds the backend Docker image, scans it for vulnerabilities using Trivy, and fails the pipeline if HIGH or CRITICAL CVEs are detected. If secure, it pushes the image to GHCR tagged with the Git commit SHA.
3. **Frontend Build, Scan, and Push**: Builds the multi-stage frontend Docker image, performs Trivy vulnerability scanning (failing on HIGH/CRITICAL severities), and pushes the image to GHCR with the Git commit SHA.

## Infrastructure as Code

The cloud infrastructure is provisioned on AWS using Terraform:

- **VPC**: A custom Virtual Private Cloud is created with public subnets across multiple availability zones, DNS support, and DNS hostnames enabled.
- **Amazon EKS**: A fully managed Kubernetes cluster is provisioned with a single managed worker node group for running containerized workloads.

All Terraform configuration files are located in the `terraform/` directory.

## Kubernetes & Observability

The application is deployed to the EKS cluster using a custom Helm chart located in the `helm/todo-app/` directory. The chart includes:

- Backend and frontend deployments with configurable replica counts
- ClusterIP services for internal communication
- Ingress resource for routing traffic (`/api` to backend, `/` to frontend)

### Observability

The backend is instrumented with `prometheus-fastapi-instrumentator`, exposing a `/metrics` endpoint for Prometheus to scrape. The monitoring configuration includes:

- **Prometheus**: Configured via `monitoring/prometheus-values.yaml` to scrape the backend service's `/metrics` endpoint for application metrics
- **Grafana**: Configured via `monitoring/grafana-values.yaml` with Prometheus as the default datasource for metric visualization

These configurations can be deployed using the official Prometheus and Grafana Helm charts with the provided values files.
