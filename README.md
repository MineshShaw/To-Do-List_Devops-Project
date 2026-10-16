# End-to-End DevSecOps Capstone Project

A complete, production-style **DevSecOps** pipeline wrapped around a small containerized To-Do
application. The project demonstrates the full lifecycle: infrastructure as code on AWS,
multi-stage container builds, a security-gated CI/CD pipeline, Kubernetes orchestration, and a
Prometheus/Grafana observability stack.

The application (FastAPI + vanilla JS + PostgreSQL) is intentionally lightweight so the focus stays
on the engineering practices around it — provisioning, scanning, shipping, and monitoring.

---

## 1. Project Overview

Every change pushed to `main` flows through an automated, security-first pipeline:

- **Infrastructure as Code** — Terraform provisions an Amazon EKS cluster (Kubernetes `1.31`) in
  `ap-southeast-2`, consuming the account's existing default VPC via data sources.
- **Containerization** — Backend and frontend are built with multi-stage Dockerfiles and run as
  non-root users.
- **CI/CD** — GitHub Actions runs the build/test/scan/publish workflow; passing images are pushed
  to Docker Hub, tagged with the Git commit SHA.
- **DevSecOps** — Gitleaks (secrets), Bandit (Python SAST), Checkov (Terraform IaC), and Trivy
  (container vulnerability scanning) act as hard gates before anything is published.
- **Observability** — The cluster runs the Prometheus/Grafana monitoring stack, scraping the
  backend's `/metrics` endpoint.

---

## 2. Architecture & Technology Stack

```
 Developer push ──▶ GitHub Actions (DevSecOps pipeline)
                        │  Gitleaks · Bandit · Checkov · Pytest · Trivy
                        ▼
                   Docker Hub (todo-backend / todo-frontend : <git-sha>)
                        │
                        ▼
     AWS ap-southeast-2 ── EKS (Kubernetes 1.31) ──┬── Frontend (nginx :8080)
                                                   ├── Backend (FastAPI :8000)
                                                   ├── PostgreSQL
                                                   └── Prometheus + Grafana
```

| Category | Technology / Version |
|---|---|
| Cloud provider | **AWS** — region `ap-southeast-2` (Sydney) |
| Orchestration | **Amazon EKS**, **Kubernetes `1.31`** |
| Infrastructure as Code | **Terraform** (`>= 1.0`), **AWS provider `~> 5.0`**, **EKS module `~> 20.0`** |
| CI/CD | **GitHub Actions** (`.github/workflows/ci-cd.yml`) |
| Container registry | **Docker Hub** |
| Container scanning (SCA) | **Trivy** (fails on `HIGH,CRITICAL`) |
| Secret scanning | **Gitleaks** |
| SAST | **Bandit** (Python) |
| IaC scanning | **Checkov** (Terraform) |
| Backend | Python 3.11, **FastAPI**, SQLAlchemy 2.x, Alembic, Uvicorn |
| Auth | JWT bearer tokens (`python-jose`), bcrypt password hashing |
| Frontend | Vanilla HTML/CSS/JS served by nginx |
| Database | **PostgreSQL 15** (production), SQLite in-memory (tests) |
| Packaging | **Helm** (`helm/todo-app/`) |
| Observability | **Prometheus** + **Grafana** |

---

## 3. Infrastructure Configuration & Academic Constraints

All infrastructure is defined in [`terraform/`](terraform/) and provisioned with Terraform.
The cluster is created by the `eks` module in [`terraform/eks.tf`](terraform/eks.tf) using the
official `terraform-aws-modules/eks/aws` module (`~> 20.0`).

### Core configuration

| Setting | Value | Location |
|---|---|---|
| Region | `ap-southeast-2` | `terraform/variables.tf` |
| Cluster name | `todo-cluster` (default) | `terraform/variables.tf` |
| Kubernetes version | `1.31` | `terraform/eks.tf` |
| EKS module | `terraform-aws-modules/eks/aws` `~> 20.0` | `terraform/eks.tf` |
| Node group | managed, `t3.small`, `ON_DEMAND`, min 1 / desired 2 / max 3 | `terraform/eks.tf` |
| Control-plane logs | `api, audit, authenticator, controllerManager, scheduler` (365-day retention) | `terraform/eks.tf` |
| Outputs | `cluster_endpoint`, `cluster_security_group_id`, `region`, `cluster_name` | `terraform/outputs.tf` |

### Workarounds for AWS sandbox IAM SCP restrictions

The account runs inside a restricted academic sandbox where an **IAM Service Control Policy (SCP)**
blocks several actions the EKS module attempts by default (notably `kms:TagResource` and the
creation of the OIDC provider used by IRSA). The following deliberate workarounds were implemented:

**1. Use existing default VPC via data sources instead of creating a new VPC** — [`terraform/vpc.tf`](terraform/vpc.tf)

The SCP restricts creating networking resources, so the configuration reads the account's existing
default VPC and subnets rather than provisioning new ones:

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

**2. `create_kms_key = false`** — to bypass `kms:TagResource` restrictions

The SCP blocks tagging KMS keys, which the module performs when it creates a dedicated key for
secret envelope encryption. Disabling the key (and the associated encryption config) avoids the
blocked API call:

```hcl
create_kms_key            = false
cluster_encryption_config = {}
```

**3. `enable_irsa = false`** — to bypass OIDC / IAM role limitations

IRSA requires creating an IAM OpenID Connect provider, which the sandbox denies. Disabling IRSA
skips OIDC provider creation and the associated per-service-account IAM roles:

```hcl
enable_irsa = false
```

**4. `enable_cluster_creator_admin_permissions = true`** — to resolve kubectl access lockouts

In EKS module v20+, the identity that creates the cluster is **no longer granted `system:masters`
admin access automatically**. Without this, `aws eks update-kubeconfig` succeeds but `kubectl`
returns `Unauthorized`. Explicitly enabling creator admin permissions restores access:

```hcl
enable_cluster_creator_admin_permissions = true
```

> **Trade-off:** these settings trade some production hardening (dedicated KMS encryption and
> fine-grained IRSA roles) for compatibility with the sandbox SCP. In an unrestricted account you
> would enable IRSA and a customer-managed KMS key.

---

## 4. CI/CD Pipeline Stages

The workflow is defined in [`.github/workflows/ci-cd.yml`](.github/workflows/ci-cd.yml) and is
triggered on **pushes to `main`** (and manually via `workflow_dispatch`). It runs with a
least-privilege token (`contents: read`, `security-events: write`) and uses `needs:` so a failed
gate stops the pipeline before any image is built or pushed.

### Stage 1 — Pre-Build Security Scanning

| Job | Tool | What it does |
|---|---|---|
| `secret-scan` | `gitleaks/gitleaks-action@v2` | Scans full git history (`fetch-depth: 0`) for committed secrets / API keys |
| `sast-backend` | `PyCQA/bandit-action@v1` | Static analysis of `backend/app` (`severity: high`), plus an explicit gate step that fails on any HIGH finding |
| `iac-scan` | `bridgecrewio/checkov-action@master` | Scans the `terraform/` directory for misconfigurations (`soft_fail: false`) |

### Stage 2 — Application Testing

| Job | Tool | What it does |
|---|---|---|
| `test-backend` | Pytest | `needs: [secret-scan, sast-backend]`. Sets up Python 3.11 with pip caching, installs `backend/requirements.txt`, runs the Pytest suite |

### Stage 3 — Build & Container Security (SCA)

| Job | Tool | What it does |
|---|---|---|
| `build-scan-backend` | Docker + **Trivy** | `needs: test-backend`. Builds `todo-backend:<sha>`, scans with `severity: HIGH,CRITICAL` and `exit-code: '1'`, saves a tarball, uploads it as an artifact |
| `build-scan-frontend` | Docker + **Trivy** | `needs: test-backend`. Same flow for `todo-frontend:<sha>` |

### Stage 4 — Registry Push

| Job | Tool | What it does |
|---|---|---|
| `push-backend` | `docker/login-action@v3` | `needs: build-scan-backend`. Downloads the artifact, loads the image, logs in to Docker Hub, pushes `${DOCKERHUB_USERNAME}/todo-backend:<sha>` |
| `push-frontend` | `docker/login-action@v3` | `needs: build-scan-frontend`. Pushes `${DOCKERHUB_USERNAME}/todo-frontend:<sha>` |

**Required repository secrets:** `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`
(and optionally `GITLEAKS_LICENSE` for org-owned private repos).

---

## 5. Deployment Guide

### 5.1 Provision the infrastructure (Terraform)

```bash
cd terraform
terraform init
terraform fmt
terraform validate
terraform plan
terraform apply
```

### 5.2 Configure kubectl

```bash
aws eks update-kubeconfig --region ap-southeast-2 --name todo-cluster
kubectl get nodes
```

### 5.3 Deploy the application (Helm)

```bash
kubectl apply -f k8s/namespace.yaml

helm upgrade --install todo-app ./helm/todo-app \
  --namespace todo-app --create-namespace \
  --set backend.image.repository=<dockerhub-user>/todo-backend \
  --set backend.image.tag=<git-sha> \
  --set frontend.image.repository=<dockerhub-user>/todo-frontend \
  --set frontend.image.tag=<git-sha>

kubectl get pods -n todo-app
kubectl get svc  -n todo-app
```

### 5.4 Deploy the monitoring stack (kube-prometheus-stack)

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm upgrade --install monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring --create-namespace

kubectl get pods -n monitoring
```

Access Grafana (default credentials `admin` / `prometheus`):

```bash
kubectl port-forward -n monitoring svc/monitoring-grafana 3000:80
# then open http://localhost:3000
```

### 5.5 Local development (optional)

```bash
docker compose up --build
# frontend: http://localhost:3000
# backend:  http://localhost:8000  (docs at /docs, metrics at /metrics)
```

---

## 6. Project Evidence

The following artifacts were captured for academic grading:

| Evidence | Path | Shows |
|---|---|---|
| Terraform init / fmt / validate | `screenshots/terraform_init_fmt_validate.png` | Terraform working directory initialised and configuration valid |
| Terraform plan | `evidence/07-terraform-plan.txt` | Planned AWS resources before apply |
| Terraform apply | `evidence/08-terraform-apply.txt` | Successful infrastructure provisioning |
| AWS EKS console | `screenshots/aws_eks_console.png` | Cluster visible in the AWS console |
| Deployed nodes | `screenshots/deployed_nodes.png` | `kubectl get nodes` showing the managed node group |
| CI/CD workflow | `screenshots/ci_cd_workflow_github_actions.png` | GitHub Actions pipeline run (scan → test → build → push) |
| Pytest results | `screenshots/pytest.png` | Backend test suite passing |
| Docker Compose | `screenshots/docker_compose.png` | Local stack running via `docker compose up` |
| Docker Hub registry | `screenshots/docker_hub_registery.png` | Pushed backend/frontend images tagged with the commit SHA |
| Grafana dashboard | `screenshots/grafana_dashboard.png` | Prometheus metrics visualised in Grafana |
| Running application | `screenshots/browser_view.png` | To-Do app served in the browser |
