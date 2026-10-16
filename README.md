# To-Do List — DevOps Capstone Project

A production-style, containerized To-Do web application used as the target workload for a full
**DevSecOps** toolchain: multi-stage Docker builds, automated security scanning, infrastructure as
code on AWS, Kubernetes orchestration, and a Prometheus/Grafana observability stack.

The application itself is deliberately small (FastAPI + vanilla JS + PostgreSQL) so the focus
stays on the delivery pipeline, infrastructure, and operational practices around it.

---

## Table of Contents

- [Architecture](#architecture)
- [Technology Stack](#technology-stack)
- [Repository Structure](#repository-structure)
- [Application](#application)
- [Local Development](#local-development)
- [CI/CD Pipeline](#cicd-pipeline)
- [Infrastructure as Code (Terraform)](#infrastructure-as-code-terraform)
- [Academic Environment Constraints](#academic-environment-constraints)
- [Kubernetes Deployment (Helm)](#kubernetes-deployment-helm)
- [Observability](#observability)
- [Security Practices](#security-practices)
- [Teardown](#teardown)

---

## Architecture

```
                          ┌──────────────────────── GitHub ────────────────────────┐
                          │  GitHub Actions — DevSecOps pipeline                   │
                          │  Gitleaks → Bandit → Checkov → Pytest → Trivy → Push   │
                          └───────────────────────────┬────────────────────────────┘
                                                      │ images
                                                      ▼
                                             ┌────────────────┐
                                             │   Docker Hub   │
                                             └───────┬────────┘
                                                     │ pull
                                                     ▼
   ┌──────────────────────────── AWS (ap-southeast-2) ────────────────────────────┐
   │  EKS Cluster (Kubernetes 1.31)                                               │
   │                                                                              │
   │   ┌────────────────┐        /api        ┌────────────────────────────────┐   │
   │   │  Frontend      │◀──────────────────▶│  Backend (FastAPI, :8000)      │   │
   │   │  nginx  :8080  │      Ingress       │  JWT auth · /metrics           │   │
   │   └────────────────┘                    └───────────────┬────────────────┘   │
   │                                                         │ SQLAlchemy         │
   │                                                         ▼                    │
   │                                                  ┌─────────────┐             │
   │                                                  │ PostgreSQL  │             │
   │                                                  └─────────────┘             │
   │                                                                              │
   │   ┌──────────────────────────────────────────────────────────────────────┐   │
   │   │ monitoring ns: Prometheus (scrape) + Grafana (dashboards)            │   │
   │   └──────────────────────────────────────────────────────────────────────┘   │
   └──────────────────────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.11, FastAPI, SQLAlchemy 2.x, Alembic, Uvicorn |
| **Auth** | JWT bearer tokens (python-jose), bcrypt password hashing, OAuth2 password flow |
| **Frontend** | Vanilla HTML/CSS/JavaScript (served by nginx) |
| **Database** | PostgreSQL 15 (production/compose), SQLite in-memory (tests) |
| **Containerization** | Docker multi-stage builds, Docker Compose |
| **CI/CD** | GitHub Actions, Docker Hub registry |
| **Security Scanning** | Gitleaks (secrets), Bandit (SAST), Checkov (IaC), Trivy (container SCA) |
| **Infrastructure** | Terraform, `terraform-aws-modules/eks/aws` v20, AWS VPC data sources |
| **Cloud** | AWS EKS — region `ap-southeast-2` (Sydney), Kubernetes `1.31` |
| **Orchestration** | Kubernetes, Helm |
| **Observability** | Prometheus (`prometheus-community`) + Grafana (`grafana`) Helm charts, `/metrics` endpoint |
| **Testing** | Pytest, HTTPX TestClient, coverage |

---

## Repository Structure

```
.
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app, JWT auth, routes
│   │   ├── models.py        # SQLAlchemy User + Task models
│   │   ├── schemas.py       # Pydantic request/response models
│   │   ├── crud.py          # Owner-scoped database operations
│   │   └── database.py      # Engine / session / Base
│   ├── alembic/             # Migration environment
│   ├── tests/               # Pytest suite (conftest + test_main)
│   ├── requirements.txt
│   └── Dockerfile           # Multi-stage, non-root runtime
├── frontend/
│   ├── index.html
│   ├── app.js               # Login/signup, JWT in localStorage, task UI
│   ├── style.css
│   ├── nginx.conf
│   └── Dockerfile           # node build → nginx runtime, non-root
├── terraform/
│   ├── providers.tf         # AWS provider (~> 5.0)
│   ├── variables.tf         # region, cluster_name, vpc_cidr
│   ├── vpc.tf               # Default VPC / subnet data sources
│   ├── eks.tf               # EKS module v20, Kubernetes 1.31
│   └── outputs.tf           # Cluster endpoint, SG, region, name
├── helm/todo-app/           # Helm chart (backend, frontend, ingress)
├── monitoring/              # Prometheus & Grafana values
├── k8s/namespace.yaml
├── docker-compose.yml       # Local full stack
├── build_and_deploy.sh      # End-to-end deploy helper
└── .github/workflows/ci-cd.yml
```

---

## Application

### Features

- **User accounts** — sign up and log in; passwords hashed with bcrypt.
- **JWT authentication** — every task endpoint requires a Bearer token.
- **Per-user data isolation** — users can only read, update, or delete their own tasks.
- **Task lifecycle** — each task has a `status` (`pending`, `in-progress`, `done`), an optional
  `description`, and an optional `due_date`.
- **Filtering** — `GET /tasks?status=pending`.
- **Observability** — Prometheus metrics exposed at `/metrics`.

### API Reference

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/health` | No | Liveness probe |
| `GET` | `/metrics` | No | Prometheus metrics |
| `POST` | `/signup` | No | Register a user, returns a JWT (`201`) |
| `POST` | `/login` | No | OAuth2 password flow, returns a JWT |
| `GET` | `/tasks?status=` | Yes | List the current user's tasks (optional status filter) |
| `POST` | `/tasks` | Yes | Create a task owned by the caller |
| `GET` | `/tasks/{id}` | Yes | Fetch one of the caller's tasks |
| `PUT` | `/tasks/{id}` | Yes | Update one of the caller's tasks |
| `DELETE` | `/tasks/{id}` | Yes | Delete one of the caller's tasks |

Accessing another user's task returns `404 Not Found`; missing/invalid tokens return
`401 Unauthorized`; invalid status values return `422 Unprocessable Entity`.

```bash
# Register and capture a token
TOKEN=$(curl -s -X POST http://localhost:8000/signup \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"secret123"}' | jq -r .access_token)

# Create a task
curl -X POST http://localhost:8000/tasks \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"title":"Ship release","status":"in-progress","due_date":"2026-01-15"}'

# Filter
curl "http://localhost:8000/tasks?status=pending" -H "Authorization: Bearer $TOKEN"
```

---

## Local Development

Bring up the full stack (PostgreSQL + backend + frontend) with Docker Compose:

```bash
docker compose up --build
```

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API docs (Swagger) | http://localhost:8000/docs |
| Metrics | http://localhost:8000/metrics |

### Running the tests

```bash
cd backend
PYTHONPATH=$PWD DATABASE_URL=sqlite:///:memory: python -m pytest -v
```

Or use the helper: `./test.sh` (adds coverage reporting).

The suite covers auth failures (401), cross-user data isolation (403/404), status filtering,
and request validation (422), using an in-memory SQLite database per test.

### Database migrations

```bash
cd backend
export DATABASE_URL="postgresql+psycopg2://postgres:postgres@localhost:5432/todo_db"
alembic revision --autogenerate -m "describe your change"
alembic upgrade head
```

---

## CI/CD Pipeline

Defined in [`.github/workflows/ci-cd.yml`](.github/workflows/ci-cd.yml), triggered on pushes to
`main`. The pipeline is a four-stage **DevSecOps** gate — no artifact is built or published until
the earlier security checks pass (`needs:` dependencies enforce fail-fast ordering).

| Stage | Job | Tool | Gate |
|---|---|---|---|
| **1 · Pre-build** | `secret-scan` | Gitleaks | Fails on committed secrets/API keys |
| | `sast-backend` | Bandit | Fails on HIGH-severity Python issues |
| | `iac-scan` | Checkov | Terraform misconfiguration scan |
| **2 · Test** | `test-backend` | Pytest | Unit/integration tests must pass |
| **3 · Build + SCA** | `build-scan-backend` | Docker + Trivy | Builds image, fails on HIGH/CRITICAL CVEs |
| | `build-scan-frontend` | Docker + Trivy | Builds image, fails on HIGH/CRITICAL CVEs |
| **4 · Publish** | `push-backend` / `push-frontend` | Docker Hub | Pushes only scanned, passing images |

**Registry:** images are pushed to **Docker Hub** as
`<DOCKERHUB_USERNAME>/todo-backend:<git-sha>` and `<DOCKERHUB_USERNAME>/todo-frontend:<git-sha>`.

**Required repository secrets:**

| Secret | Purpose |
|---|---|
| `DOCKERHUB_USERNAME` | Docker Hub account |
| `DOCKERHUB_TOKEN` | Docker Hub access token |
| `GITLEAKS_LICENSE` | Optional — only for org-owned private repos |

---

## Infrastructure as Code (Terraform)

All infrastructure lives in [`terraform/`](terraform/) and is provisioned with Terraform.

| Setting | Value |
|---|---|
| Region | `ap-southeast-2` (Sydney) |
| Cluster name | `todo-cluster` (default) |
| Kubernetes version | `1.31` |
| EKS module | `terraform-aws-modules/eks/aws` `~> 20.0` |
| AWS provider | `hashicorp/aws` `~> 5.0` |
| Networking | **Default VPC/subnets consumed via data sources** |
| Node group | Managed, `t3.small`, `ON_DEMAND`, min 1 / desired 2 / max 3 |
| Control-plane logs | api, audit, authenticator, controllerManager, scheduler (365-day retention) |

Rather than creating a bespoke VPC, `terraform/vpc.tf` **references the existing default VPC**:

```hcl
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}
```

```bash
cd terraform
terraform init
terraform fmt
terraform validate
terraform plan
terraform apply
aws eks update-kubeconfig --region ap-southeast-2 --name todo-cluster
```

**Outputs:** `cluster_endpoint`, `cluster_security_group_id`, `region`, `cluster_name`.

---

## Academic Environment Constraints

This project runs inside a restricted AWS sandbox where an **IAM Service Control Policy (SCP)**
blocks several IAM actions that the EKS module attempts by default (for example `kms:TagResource`
and `iam:CreateOpenIDConnectProvider`). To work within those guardrails, two configuration changes
are applied in `terraform/eks.tf`:

| Setting | Value | Reason |
|---|---|---|
| `create_kms_key` | `false` | Skips dedicated KMS key creation, which the SCP blocks at `kms:TagResource`. |
| `cluster_encryption_config` | `{}` | Disables envelope-encryption wiring tied to that KMS key. |
| `enable_irsa` | `false` | Skips creating the IAM OIDC provider for IRSA, avoiding the blocked `iam:CreateOpenIDConnectProvider`. |
| `enable_cluster_creator_admin_permissions` | `true` | Grants the IAM identity that creates the cluster admin access, since IRSA-based access is unavailable. |

> These adjustments trade some production hardening (KMS encryption, fine-grained IRSA roles) for
> compatibility with the sandbox. In an unrestricted account you would enable IRSA and a customer
> managed KMS key.

---

## Kubernetes Deployment (Helm)

The application is packaged as a Helm chart in [`helm/todo-app/`](helm/todo-app/):

- Backend Deployment + ClusterIP Service (`:80` → `:8000`)
- Frontend Deployment + ClusterIP Service (`:80` → `:8080`)
- Ingress routing `/api` to the backend and `/` to the frontend
- Configurable replicas and per-container resource requests/limits
- Hardened pod security contexts (non-root, read-only capabilities, `RuntimeDefault` seccomp)

```bash
kubectl apply -f k8s/namespace.yaml
helm upgrade --install todo-app ./helm/todo-app --namespace todo-app --create-namespace
kubectl get pods -n todo-app
kubectl get svc  -n todo-app
```

---

## Observability

Monitoring runs in the `monitoring` namespace as **two Helm releases** — Prometheus
(`prometheus-community/prometheus`) and Grafana (`grafana/grafana`) — configured by the values
files in [`monitoring/`](monitoring/).

**Prometheus** — [`monitoring/prometheus-values.yaml`](monitoring/prometheus-values.yaml):

- 15s global scrape interval; persistent volumes disabled (ephemeral, lab-friendly).
- Scrapes itself **and the backend**, the latter on a shorter 10s interval:

  ```yaml
  - job_name: 'todo-backend'
    static_configs:
      - targets: ['todo-app-backend-service:80']
    metrics_path: /metrics
    scrape_interval: 10s
  ```

- `nodeExporter` and `kubeStateMetrics` enabled; `alertmanager` and `pushgateway` disabled.

**Grafana** — [`monitoring/grafana-values.yaml`](monitoring/grafana-values.yaml):

- Prometheus provisioned as the default datasource (`http://prometheus-server`).
- ClusterIP service on port 80; persistence disabled (default credentials `admin` / `admin`).

The backend exposes its metrics via `prometheus-fastapi-instrumentator` at `/metrics`.

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

helm upgrade --install prometheus prometheus-community/prometheus \
  --namespace monitoring --create-namespace \
  --values monitoring/prometheus-values.yaml

helm upgrade --install grafana grafana/grafana \
  --namespace monitoring --create-namespace \
  --values monitoring/grafana-values.yaml
```

Access Grafana locally (then log in with `admin` / `admin`):

```bash
kubectl port-forward -n monitoring svc/grafana 3000:80
```

---

## Security Practices

- **Shift-left scanning** — secrets, Python SAST, and Terraform IaC are scanned before any build.
- **Container SCA** — Trivy blocks images containing HIGH/CRITICAL vulnerabilities before publish.
- **Least-privilege CI token** — the workflow runs with `contents: read` and `security-events: write`.
- **Non-root containers** — both images run as UID 1001 with dropped capabilities.
- **Scoped data access** — every task query is filtered by the authenticated user's ID.
- **No secrets in images** — configuration (DB URL, JWT secret) is injected via environment variables.

---

## Teardown

```bash
# Local stack
docker compose down -v

# Helm release
helm uninstall todo-app --namespace todo-app
helm uninstall prometheus grafana --namespace monitoring

# AWS infrastructure
cd terraform
terraform destroy
```

---

*Academic DevOps capstone project — infrastructure, pipeline, and observability demonstration.*
