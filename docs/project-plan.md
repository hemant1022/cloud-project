# Project Plan — Deploy 3-Tier App on EKS

Five phases. Each phase lists deliverables, the folders it touches, and acceptance criteria.

## Phase 0 — Scaffold (done)

- [x] Directory tree for every phase and tech stack
- [x] Per-stack logging convention (`logs/<stack>/`)
- [x] Docs: plan, architecture, decisions, runbook
- [x] Terraform / Node / logs / env entries in `.gitignore`

Acceptance: `git status` shows only intended scaffold files.

## Phase 1 — Application Containerization

Folders: `app/frontend`, `app/backend`, `app/db`, `docker`, `logs/docker`

- [ ] React + Vite frontend (multi-stage: node build → nginx runtime)
- [ ] FastAPI backend (multi-stage: python builder → slim runtime)
- [ ] PostgreSQL schema + seed in `app/db/init.sql`
- [ ] `docker/docker-compose.yml` with healthchecks and a shared network
- [ ] `.env.example` for local environment variables

Acceptance: `docker compose up` starts all three services; `GET /health` returns 200;
schema is created; run log written to `logs/docker/`.

## Phase 2 — Infrastructure as Code (Terraform + EKS)

Folders: `infra/bootstrap`, `infra/modules/{vpc,eks,iam-oidc}`, `infra/envs/dev`, `logs/terraform`

- [ ] Bootstrap: S3 bucket (versioned, encrypted) + DynamoDB state lock
- [ ] VPC module: 2 public / 2 private subnets, NAT, IGW, route tables, EKS tags
- [ ] EKS module: control plane + managed node group (t3.medium x2)
- [ ] IAM/OIDC module: IRSA roles for EBS CSI and AWS Load Balancer Controller
- [ ] `dev` environment wiring modules with remote backend

Acceptance: `terraform apply` succeeds; `kubectl get nodes` shows Ready nodes;
logs written to `logs/terraform/`.

## Phase 3 — CI Pipeline (GitHub Actions)

Folders: `.github/workflows`, `scripts/ci`, `logs/ci`

- [ ] Trigger on pull_request and push to `main`
- [ ] Unit tests for frontend and backend
- [ ] Authenticate to ECR (prefer GitHub OIDC role over static keys)
- [ ] Build images tagged `sha-${{ github.sha }}`
- [ ] Push to ECR
- [ ] Bump image tags in `k8s/overlays/dev/kustomization.yaml` (GitOps hand-off)

Acceptance: workflow green; images present in ECR; bot commit updates manifest tags.

## Phase 4 — GitOps Deployment (ArgoCD)

Folders: `k8s/base`, `k8s/overlays/{dev,prod}`, `k8s/argocd`, `logs/argocd`

- [ ] Kustomize base: Deployments, Services, ConfigMap, Secret template, Ingress, PVC
- [ ] Overlays for dev/prod (image tags, replicas, resources)
- [ ] Install ArgoCD in namespace `argocd`
- [ ] App-of-apps Application CRD with auto-sync + self-heal + prune

Acceptance: ArgoCD reports `Synced/Healthy`; app reachable via ingress/LoadBalancer.

## Phase 5 — Observability (Prometheus + Grafana)

Folders: `monitoring`, `logs/monitoring`

- [ ] kube-prometheus-stack values (retention, resources, ingress)
- [ ] Alert rules: pod crashloop, high CPU, high memory, PVC pressure
- [ ] Grafana dashboard + datasource provisioning
- [ ] Validate a test alert end-to-end

Acceptance: Grafana reachable; dashboards show cluster + pod metrics; test alert fires.
