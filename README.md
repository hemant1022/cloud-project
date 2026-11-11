# Inventory Management App on AWS EKS

A production-style inventory management application deployed as a three-tier system on
Amazon EKS. Add products, manage stock, track suppliers and categories, bulk-import from
CSV, watch low-stock alerts, and see total inventory value in real time.

## Features

- Product catalog with SKU, price, cost, stock quantity, reorder level, category, and supplier
- Dashboard with total inventory value, stock health, and value by category
- Low-stock and out-of-stock alerts with one-click restocking
- CSV import with per-row validation and a downloadable template
- Admin approval queue for categories/suppliers introduced by CSV imports
- JWT authentication with `admin`, `manager`, and `viewer` roles
- Per-run and combined application logs
- Infrastructure, CI/CD, GitOps, and monitoring scaffolding for EKS

## Stack

| Layer      | Technology |
| ---------- | ---------- |
| Frontend   | React 18 + TypeScript + Vite + Tailwind + TanStack Query + Recharts |
| Backend    | FastAPI + SQLAlchemy 2 + PostgreSQL + PyJWT + Argon2 |
| Database   | PostgreSQL 16 |
| Local      | Docker Compose |
| Infra      | Terraform (VPC, EKS, IAM/OIDC) — scaffolded |
| CI/CD      | GitHub Actions → Amazon ECR — scaffolded |
| GitOps     | ArgoCD + Kustomize — scaffolded |
| Monitoring | kube-prometheus-stack — scaffolded |

## Quickstart (Docker Compose)

```powershell
Copy-Item docker/.env.example docker/.env
.\scripts\run-logged.ps1 -Stack docker -Phase 01 -Action up `
  -Command "docker compose -f docker/docker-compose.yml up -d --build"
```

- Frontend: http://localhost:8080
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/api/health

Sign in with `ADMIN_EMAIL` / `ADMIN_PASSWORD` from `docker/.env`.

Seed data loads on first database initialization. To reload after changing seed CSV files:

```powershell
docker compose -f docker/docker-compose.yml down -v
docker compose -f docker/docker-compose.yml up -d --build
```

## Seed Data

`app/db/seed/` contains a small placeholder dataset. To generate ~120 real rows from the
**CC BY 4.0 Grocery Inventory and Sales Dataset**:

1. Download the CSV from Kaggle:
   https://www.kaggle.com/datasets/salahuddinahmedshuvo/grocery-inventory-and-sales-dataset
2. Save it to `app/db/seed/raw/` (git-ignored).
3. Run:

```powershell
py -3.12 scripts\seed\adapt_ccby_grocery.py `
  --input app\db\seed\raw\Grocery_Inventory_and_Sales_Dataset.csv `
  --limit 120 --seed 42
```

See `app/db/seed/ATTRIBUTION.md` and `scripts/seed/README.md`.

## Local Development

Backend (Python 3.12):

```powershell
py -3.12 -m venv app\backend\.venv
app\backend\.venv\Scripts\pip install -r app\backend\requirements-dev.txt
Copy-Item app\backend\.env.example app\backend\.env
app\backend\.venv\Scripts\python -m uvicorn app.main:app --reload --app-dir app\backend --port 8000
```

Frontend:

```powershell
cd app\frontend
npm install
npm run dev
```

## Tests

```powershell
app\backend\.venv\Scripts\python -m pytest app\backend\tests -q
cd app\frontend; npm run build
```

## Project Structure

```
app/
  backend/    FastAPI app, routers, services, tests, Dockerfile
  frontend/   React app, pages, components, Dockerfile
  db/         init.sql + seed CSVs
docker/       docker-compose.yml + .env.example
infra/        Terraform bootstrap, modules, environments
k8s/          Kustomize base/overlays + ArgoCD apps
monitoring/   Prometheus values, alerts, Grafana dashboards
scripts/      run-logged.ps1, seed adapter
logs/         per-stack and combined run logs (git-ignored)
docs/         plan, architecture, decisions, runbook
```

## Logging

Every command can be wrapped to capture output under `logs/<stack>/`:

```powershell
.\scripts\run-logged.ps1 -Stack backend -Phase 02 -Action test -Command "app\backend\.venv\Scripts\python -m pytest app\backend\tests -q"
```

The backend also writes structured events to `logs/combined/combined.log` and
`logs/backend/backend-<timestamp>.log`, including request traces, logins, product changes,
CSV import summaries, and uncaught exceptions. See `logs/README.md`.

## Roadmap

1. Application + database + Docker (done)
2. JWT auth, approvals, CSV import (done)
3. Terraform: VPC, EKS, IAM/OIDC
4. GitHub Actions: tests, ECR push, manifest bump
5. ArgoCD GitOps deployment
6. Prometheus + Grafana monitoring
