# Decisions (ADR summary)

| # | Decision | Alternatives | Rationale |
|---|----------|--------------|-----------|
| 1 | FastAPI backend | Node/Express | Repo already Python-centric; small, typed, async |
| 2 | React + Vite frontend | Next.js | Simpler static build, tiny nginx image |
| 3 | PostgreSQL in-cluster | MongoDB, RDS | Matches classic 3-tier; avoids managed DB cost |
| 4 | Kustomize manifests | Helm charts | Easy CI image-tag bump, minimal templating |
| 5 | Monorepo with `k8s/` subfolder | Separate manifest repo | Simpler to start; can split later (ArgoCD path unchanged in spirit) |
| 6 | GitHub OIDC to AWS | Static access keys | No long-lived secrets in repo |
| 7 | Per-stack log folders | Single log file | No collisions between docker/terraform/ci/argocd/monitoring runs |
| 8 | Terraform modules wrap community modules | Fully hand-rolled | Faster, battle-tested VPC/EKS wiring |

## Naming Conventions

- Docker images: `<ecr>/<app>-<tier>:sha-<git-sha>` (e.g. `cloud-project-backend:sha-abc123`)
- Kubernetes namespaces: `app`, `argocd`, `monitoring`
- Logs: `logs/<stack>/<phase>-<action>-<yyyyMMdd-HHmmss>.log`
