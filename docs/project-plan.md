# Project Plan — Inventory Management on EKS

Each phase lists deliverables, the folders it touches, and acceptance criteria.

## Phase 0 — Scaffold (done)

- [x] Directory tree per phase and tech stack
- [x] Per-stack and combined logging (`logs/`, `logging_config.py`)
- [x] Docs: plan, architecture, decisions, runbook
- [x] Ignore rules for Terraform, Node, env files, secrets, logs

## Phase 1 — Application (done)

Folders: `app/backend`, `app/frontend`, `app/db`, `docker`

- [x] PostgreSQL schema: users, categories, suppliers, products, stock_movements, catalog_requests
- [x] FastAPI product/catalog/stats/alerts APIs
- [x] JWT auth with admin/manager/viewer roles
- [x] CSV import with per-row errors and admin approval requests
- [x] React app: login, dashboard, products, alerts, import, approvals, catalog
- [x] Docker Compose with Postgres healthcheck and seed mount
- [x] Backend tests (12) and frontend production build

Acceptance: `docker compose up` runs all three services; login works; products, alerts,
stats, and CSV import work end to end.

## Phase 2 — Seed data (done, CC BY 4.0)

Folders: `app/db/seed`, `scripts/seed`

- [x] Schema + placeholder seed loaded on first database start
- [x] Adapter `scripts/seed/adapt_ccby_grocery.py` generating ~120 products
- [x] Attribution in `app/db/seed/ATTRIBUTION.md`

Acceptance: adapter produces `categories.csv`, `suppliers.csv`, `products.csv` with
low-stock and out-of-stock rows; `down -v` then `up` loads them.

## Phase 3 — Infrastructure as Code (Terraform + EKS)

Folders: `infra/bootstrap`, `infra/modules/{vpc,eks,iam-oidc}`, `infra/envs/dev`, `logs/terraform`

- [ ] Bootstrap: S3 bucket (versioned, encrypted) + DynamoDB state lock
- [ ] VPC module: 2 public / 2 private subnets, NAT, IGW, route tables, EKS tags
- [ ] EKS module: control plane + managed node group (t3.medium x2)
- [ ] IAM/OIDC module: IRSA roles for EBS CSI and AWS Load Balancer Controller
- [ ] Dev environment wiring modules with remote backend

Acceptance: `terraform apply` succeeds; `kubectl get nodes` shows Ready nodes.

## Phase 4 — CI Pipeline (GitHub Actions)

Folders: `.github/workflows`, `logs/ci`

- [ ] Trigger on pull_request and push to `main`
- [ ] Backend pytest + frontend build
- [ ] Authenticate to ECR (prefer GitHub OIDC role over static keys)
- [ ] Build images tagged `sha-${{ github.sha }}`
- [ ] Push backend and frontend images to ECR
- [ ] Bump image tags in `k8s/overlays/dev/kustomization.yaml`

Acceptance: workflow green; images in ECR; bot commit updates manifest tags.

## Phase 5 — GitOps Deployment (ArgoCD)

Folders: `k8s/base`, `k8s/overlays/{dev,prod}`, `k8s/argocd`, `logs/argocd`

- [ ] Kustomize base: deployments, services, configmap, secret template, ingress, PVC
- [ ] Postgres StatefulSet + PVC (or external managed database)
- [ ] Overlays for dev/prod (image tags, replicas, resources)
- [ ] Install ArgoCD and create an app-of-apps Application
- [ ] Auto-sync, self-heal, prune

Acceptance: ArgoCD reports `Synced/Healthy`; app reachable via ingress/LoadBalancer.

## Phase 6 — Observability (Prometheus + Grafana)

Folders: `monitoring`, `logs/monitoring`

- [ ] kube-prometheus-stack values (retention, resources, ingress)
- [ ] Alert rules: pod crashloop, high CPU/memory, PVC pressure, low-stock metric
- [ ] Grafana dashboard and datasource provisioning
- [ ] Validate a test alert end to end

Acceptance: Grafana reachable; dashboards show cluster and app metrics; alerts fire.
