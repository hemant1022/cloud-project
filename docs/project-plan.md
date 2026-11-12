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

## Phase 4 — CI Pipeline (GitHub Actions → ECR) — workflow added

Folders: `.github/workflows`, `logs/ci`

- [ ] Trigger on pull_request and push to `main` (currently push to `main` + manual)
- [x] Backend pytest + frontend build
- [x] Authenticate to ECR with repository secrets (OIDC role recommended later)
- [x] Build images tagged `sha-${{ github.sha }}` and `latest`
- [x] Push backend, frontend, and database images to ECR
- [x] Bump image tags in `k8s/overlays/dev/kustomization.yaml`

Secrets: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`, and the
required `ECR_REPOSITORY` variable (or secret). All images are pushed to that single
repository with component tags (`backend-<sha>`, `frontend-<sha>`, `db-<sha>`).
Acceptance: workflow green; three images in ECR; bot commit updates the overlay tags
and ArgoCD syncs them.

## Phase 5 — GitOps Deployment (ArgoCD)

Folders: `k8s/base`, `k8s/overlays/{dev,prod}`, `k8s/argocd`, `logs/argocd`

- [x] Kustomize base: deployments, services, configmap, secret template, ingress, PVC
- [x] Postgres StatefulSet + PVC using an ECR-hosted DB image with seed data
- [x] Overlays for dev/prod (image tags, replicas)
- [x] App-of-apps and `inventory-dev` Application manifests
- [ ] Install ArgoCD and bootstrap the app-of-apps on the cluster
- [ ] Auto-sync, self-heal, prune verified

Acceptance: ArgoCD reports `Synced/Healthy`; app reachable via ingress/LoadBalancer.

## Phase 6 — Observability (Prometheus + Grafana)

Folders: `monitoring`, `logs/monitoring`

- [ ] kube-prometheus-stack values (retention, resources, ingress)
- [ ] Alert rules: pod crashloop, high CPU/memory, PVC pressure, low-stock metric
- [ ] Grafana dashboard and datasource provisioning
- [ ] Validate a test alert end to end

Acceptance: Grafana reachable; dashboards show cluster and app metrics; alerts fire.
