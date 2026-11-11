# Decisions (ADR summary)

| # | Decision | Alternatives | Rationale |
|---|----------|--------------|-----------|
| 1 | FastAPI backend | Node/Express | Repo is Python-centric; typed, async, auto docs |
| 2 | React + Vite frontend | Next.js | Simple static build, tiny nginx image |
| 3 | PostgreSQL in-cluster | MongoDB, RDS | Classic 3-tier; avoids managed DB cost |
| 4 | Kustomize manifests | Helm charts | Easy CI image-tag bump, minimal templating |
| 5 | Monorepo with `k8s/` subfolder | Separate manifest repo | Simpler to start; can split later |
| 6 | GitHub OIDC to AWS | Static access keys | No long-lived secrets in repo |
| 7 | Per-stack log folders + combined log | Single log file | No collisions; combined view for tracing |
| 8 | Terraform modules wrap community modules | Fully hand-rolled | Faster, battle-tested VPC/EKS wiring |
| 9 | JWT (HS256) with roles admin/manager/viewer | Session cookies, OAuth | Simple, stateless, supports role gating |
| 10 | Seed from CC BY 4.0 grocery dataset | Synthetic only | Realistic categories/suppliers/prices with attribution |
| 11 | Unknown CSV catalog values → reject + approval request | Auto-create silently | Admin keeps control of catalog quality |
| 12 | Admin-only auto-create on import (`create_missing`) | Approval for admins too | The admin is already the authorizing party |
| 13 | USD currency | INR, EUR | Chosen for this deployment |

## Naming Conventions

- Docker images: `<ecr>/inventory-<tier>:sha-<git-sha>`
- Kubernetes namespaces: `inventory`, `argocd`, `monitoring`
- Logs: `logs/<stack>/<phase>-<action>-<yyyyMMdd-HHmmss>.log`
- Python app logs: `logs/<stack>/<stack>-<dd_mm_yyyy_hh_mm_ss>.log`, plus `logs/combined/combined.log`
