# Runbook

All commands are wrapped by `scripts/run-logged.ps1` to capture output under `logs/<stack>/`.

## Prerequisites

| Tool      | Check                     | Install (Windows)                     |
| --------- | ------------------------- | ------------------------------------- |
| Docker    | `docker --version`        | Docker Desktop                        |
| Python    | `py -3.12 --version`      | `winget install Python.Python.3.12`   |
| Node      | `node --version`          | `winget install OpenJS.NodeJS.LTS`    |
| Terraform | `terraform --version`     | `winget install Hashicorp.Terraform`  |
| AWS CLI   | `aws --version`           | `winget install Amazon.AWSCLI`        |
| kubectl   | `kubectl version --client`| `winget install Kubernetes.kubectl`   |
| Helm      | `helm version`            | `winget install Helm.Helm`            |

Terraform is currently **missing** on this machine — install it before Phase 3.

## Phase 1 — Run locally with Docker Compose

```powershell
Copy-Item docker/.env.example docker/.env
.\scripts\run-logged.ps1 -Stack docker -Phase 01 -Action up `
  -Command "docker compose -f docker/docker-compose.yml up -d --build"
.\scripts\run-logged.ps1 -Stack docker -Phase 01 -Action ps `
  -Command "docker compose -f docker/docker-compose.yml ps"
```

- Frontend: http://localhost:8080
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/api/health

Sign in with `ADMIN_EMAIL` / `ADMIN_PASSWORD` from `docker/.env`.

Stop:

```powershell
docker compose -f docker/docker-compose.yml down      # keep data
docker compose -f docker/docker-compose.yml down -v   # delete data, reload seed
```

## Seed data (CC BY 4.0)

```powershell
# Download the Kaggle CSV first, save under app/db/seed/raw/
.\scripts\run-logged.ps1 -Stack backend -Phase 02 -Action seed `
  -Command "py -3.12 scripts/seed/adapt_ccby_grocery.py --input app/db/seed/raw/Grocery_Inventory_and_Sales_Dataset.csv --limit 120 --seed 42"

docker compose -f docker/docker-compose.yml down -v
docker compose -f docker/docker-compose.yml up -d --build
```

See `app/db/seed/ATTRIBUTION.md`.

## Local development (no containers)

Backend:

```powershell
py -3.12 -m venv app\backend\.venv
app\backend\.venv\Scripts\pip install -r app\backend\requirements-dev.txt
Copy-Item app\backend\.env.example app\backend\.env
app\backend\.venv\Scripts\python -m uvicorn app.main:app --reload --app-dir app\backend --port 8000
```

Frontend (proxies `/api` to port 8000):

```powershell
cd app\frontend
npm install
npm run dev
```

## Tests

```powershell
.\scripts\run-logged.ps1 -Stack backend -Phase 02 -Action tests `
  -Command "app\backend\.venv\Scripts\python -m pytest app\backend\tests -q"

cd app\frontend
npm run build
```

The backend tests use an isolated SQLite database and cover auth, roles, CRUD, stats,
alerts, stocking, and the CSV approval flow.

## API quick reference

| Method | Path | Roles |
| ------ | ---- | ----- |
| POST | `/api/auth/login` | public |
| GET | `/api/auth/me` | any authenticated |
| GET | `/api/products` | any authenticated |
| POST/PATCH | `/api/products`, `/api/products/{id}` | admin, manager |
| DELETE | `/api/products/{id}` | admin |
| POST | `/api/products/{id}/adjust` | admin, manager |
| GET | `/api/stats/summary` | any authenticated |
| GET | `/api/alerts/low-stock` | any authenticated |
| POST | `/api/categories`, `/api/suppliers` | admin |
| GET | `/api/categories`, `/api/suppliers` | any authenticated |
| POST | `/api/import` | admin, manager |
| GET | `/api/import/template` | admin, manager |
| GET | `/api/catalog-requests` | admin |
| POST | `/api/catalog-requests/{id}/approve` | admin |
| POST | `/api/catalog-requests/{id}/reject` | admin |

## Logging

```powershell
.\scripts\run-logged.ps1 -Stack backend -Phase 02 -Action test -Command "app\backend\.venv\Scripts\python -m pytest app\backend\tests -q"
```

Outputs:

- `logs/combined/combined.log` — every Python event
- `logs/backend/backend-<timestamp>.log` — per-run application log
- `logs/backend/<phase>-<action>-<timestamp>.log` — shell command output

Uncaught exceptions, failed logins, forbidden access, DB failures, and CSV import errors are
logged with stack traces.

## Phase 3 — Terraform (state backend first)

```powershell
.\scripts\run-logged.ps1 -Stack terraform -Phase 03 -Action bootstrap `
  -Command "terraform -chdir=infra/bootstrap init; terraform -chdir=infra/bootstrap apply -auto-approve"
.\scripts\run-logged.ps1 -Stack terraform -Phase 03 -Action init `
  -Command "terraform -chdir=infra/envs/dev init"
.\scripts\run-logged.ps1 -Stack terraform -Phase 03 -Action plan `
  -Command "terraform -chdir=infra/envs/dev plan -out=tfplan"
.\scripts\run-logged.ps1 -Stack terraform -Phase 03 -Action apply `
  -Command "terraform -chdir=infra/envs/dev apply tfplan"
```

Then:

```powershell
aws eks update-kubeconfig --name cloud-project-dev --region <region>
kubectl get nodes
```

## Phase 4 — CI (GitHub Actions → ECR)

`.github/workflows/aws.yaml` runs on every push to `main` (and manually):

1. Backend pytest and frontend production build.
2. Login to ECR with repository secrets.
3. Create `<prefix>-backend`, `<prefix>-frontend`, and `<prefix>-db` repos if missing.
4. Build and push all three images tagged with the full commit SHA and `latest`.
5. Bump the image tags in `k8s/overlays/dev/kustomization.yaml` and push the commit
   (ArgoCD then syncs it).

Repository secrets (Settings → Secrets and variables → Actions):

| Secret | Purpose |
| ------ | ------- |
| `AWS_ACCESS_KEY_ID` | IAM access key |
| `AWS_SECRET_ACCESS_KEY` | IAM secret key |
| `AWS_DEFAULT_REGION` | e.g. `us-east-1` |
| `ECR_REPO_PREFIX` | e.g. `inventory` → `inventory-backend`, `inventory-frontend`, `inventory-db` |

The IAM principal needs `ecr:GetAuthorizationToken`, `ecr:BatchCheckLayerAvailability`,
`ecr:InitiateLayerUpload`, `ecr:UploadLayerPart`, `ecr:CompleteLayerUpload`,
`ecr:PutImage`, `ecr:BatchGetImage`, plus `ecr:DescribeRepositories`/`ecr:CreateRepository`
for the one-time repo creation. Prefer an OIDC role instead of static keys when possible.

Run the same checks locally before pushing:

```powershell
.\scripts\run-logged.ps1 -Stack ci -Phase 04 -Action tests `
  -Command "app\backend\.venv\Scripts\python -m pytest app\backend\tests -q"
cd app\frontend; npm run build
kubectl kustomize k8s/overlays/dev > $null
```

## Phase 5 — ArgoCD

Create the application secret once the cluster and namespace exist:

```powershell
kubectl create namespace inventory --dry-run=client -o yaml | kubectl apply -f -
kubectl -n inventory create secret generic inventory-secrets `
  --from-literal=POSTGRES_PASSWORD='<password>' `
  --from-literal=DATABASE_URL='postgresql+psycopg2://inventory:<password>@db:5432/inventory' `
  --from-literal=JWT_SECRET='<long-random-string>' `
  --from-literal=ADMIN_EMAIL='admin@example.com' `
  --from-literal=ADMIN_PASSWORD='<strong-password>'
```

Install ArgoCD and register the app-of-apps:

```powershell
.\scripts\run-logged.ps1 -Stack argocd -Phase 05 -Action install `
  -Command "kubectl create namespace argocd; kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml"
.\scripts\run-logged.ps1 -Stack argocd -Phase 05 -Action app `
  -Command "kubectl apply -f k8s/argocd/app-of-apps.yaml"
```

`inventory-apps` syncs `k8s/argocd/apps/`, which contains `inventory-dev` pointing at
`k8s/overlays/dev`. Image tags there are updated by CI; do not edit them by hand.
Verify the placeholders in the overlay have been replaced with real ECR URIs:

```powershell
kubectl kustomize k8s/overlays/dev | Select-String "image:"
```

UI: `kubectl -n argocd port-forward svc/argocd-server 8080:443`

Initial password: `kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | %{[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($_))}`

## Phase 6 — Monitoring

```powershell
.\scripts\run-logged.ps1 -Stack monitoring -Phase 06 -Action install `
  -Command "helm repo add prometheus-community https://prometheus-community.github.io/helm-charts; helm repo update; helm upgrade --install prometheus prometheus-community/kube-prometheus-stack -n monitoring --create-namespace -f monitoring/prometheus/values.yaml"
.\scripts\run-logged.ps1 -Stack monitoring -Phase 06 -Action port-forward `
  -Command "kubectl -n monitoring port-forward svc/prometheus-grafana 3000:80"
```

Grafana: http://localhost:3000 (default `admin` / `prom-operator` unless overridden).

## Teardown (avoid AWS charges)

```powershell
.\scripts\run-logged.ps1 -Stack terraform -Phase 03 -Action destroy `
  -Command "terraform -chdir=infra/envs/dev destroy -auto-approve"
```

Destroy the EKS environment before the bootstrap bucket. Remove leftover ELBs, ENIs, and
EBS volumes created by Kubernetes, then delete the S3 bucket and DynamoDB table.
