# Cloud Project — 3-Tier App on AWS EKS

End-to-end project that containerizes a three-tier application, provisions EKS with Terraform,
ships it through a GitHub Actions CI pipeline, deploys it with ArgoCD (GitOps), and monitors it
with Prometheus + Grafana.

## Components

| Layer      | Stack                                            |
| ---------- | ------------------------------------------------ |
| Frontend   | React + Vite, served by nginx (multi-stage image) |
| Backend    | Python FastAPI (multi-stage image)               |
| Database   | PostgreSQL (StatefulSet + PVC)                   |
| Infra      | Terraform — VPC, EKS, IAM/OIDC (IRSA)            |
| CI         | GitHub Actions → Amazon ECR                     |
| GitOps     | ArgoCD + Kustomize                              |
| Monitoring | kube-prometheus-stack (Prometheus + Grafana)    |

## Repository Layout

```
app/        Application source (frontend, backend, db)
docker/     Local docker-compose orchestration
infra/      Terraform bootstrap + modules + environments
.github/    CI workflows
k8s/        Kustomize base/overlays + ArgoCD applications
monitoring/ Prometheus values, alert rules, Grafana dashboards
scripts/    Helper scripts grouped per stack
logs/       Per-stack run logs (generated, not committed)
docs/       Plan, architecture, decisions, runbook
```

## Phase Status

| Phase | Scope                              | Status |
| ----- | ---------------------------------- | ------ |
| 0     | Project scaffold + logging         | Done   |
| 1     | Containerize app + docker compose  | Todo   |
| 2     | Provision EKS with Terraform       | Todo   |
| 3     | CI/CD with GitHub Actions          | Todo   |
| 4     | GitOps deployment with ArgoCD      | Todo   |
| 5     | Prometheus + Grafana monitoring    | Todo   |

## Documentation

- [Project plan](docs/project-plan.md)
- [Architecture](docs/architecture.md)
- [Decisions](docs/decisions.md)
- [Runbook](docs/runbook.md)

## Logging Every Run

All commands are executed through `scripts/run-logged.ps1` so output is captured per stack:

```powershell
.\scripts\run-logged.ps1 -Stack terraform -Phase 02 -Action plan -Command "terraform -chdir=infra/envs/dev plan"
```

Logs land in `logs/<stack>/` and are git-ignored. See [logs/README.md](logs/README.md).
