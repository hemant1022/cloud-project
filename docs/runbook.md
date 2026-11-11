# Runbook

All commands are wrapped by `scripts/run-logged.ps1` to capture output under `logs/<stack>/`.

## Prerequisites

| Tool      | Check                     | Install (Windows)                        |
| --------- | ------------------------- | ---------------------------------------- |
| Docker    | `docker --version`        | Docker Desktop                           |
| Terraform | `terraform --version`     | `winget install Hashicorp.Terraform`     |
| AWS CLI   | `aws --version`           | `winget install Amazon.AWSCLI`           |
| kubectl   | `kubectl version --client`| `winget install Kubernetes.kubectl`      |
| Helm      | `helm version`            | `winget install Helm.Helm`               |
| Node      | `node --version`          | `winget install OpenJS.NodeJS.LTS`       |
| Python    | `python --version`        | `winget install Python.Python.3.12`      |

Terraform is currently **missing** on this machine — install it before Phase 2.

## Application logging

The Python logger writes each event to a combined rolling file and a per-run stack file:

```powershell
.\scripts\run-logged.ps1 -Stack backend -Phase 00 -Action self-test -Command "python app/backend/app/logging_config.py"
```

Or from Python:

```python
from app.logging_config import configure_logger, get_logger

configure_logger(stack="backend")
logger = get_logger(__name__)
logger.info("backend started")
```

Outputs: `logs/combined/combined.log` and `logs/backend/backend-<dd_mm_yyyy_hh_mm_ss>.log`.
Override the stack with `LOG_STACK`, the root with `LOG_DIR` or `PROJECT_ROOT`.

## Phase 1 — Local containers

```powershell
.\scripts\run-logged.ps1 -Stack docker -Phase 01 -Action compose-up -Command "docker compose -f docker/docker-compose.yml up -d --build"
.\scripts\run-logged.ps1 -Stack docker -Phase 01 -Action ps -Command "docker compose -f docker/docker-compose.yml ps"
.\scripts\run-logged.ps1 -Stack docker -Phase 01 -Action compose-down -Command "docker compose -f docker/docker-compose.yml down -v"
```

## Phase 2 — Terraform (state backend first)

```powershell
.\scripts\run-logged.ps1 -Stack terraform -Phase 02 -Action bootstrap -Command "terraform -chdir=infra/bootstrap init; terraform -chdir=infra/bootstrap apply -auto-approve"
.\scripts\run-logged.ps1 -Stack terraform -Phase 02 -Action init -Command "terraform -chdir=infra/envs/dev init"
.\scripts\run-logged.ps1 -Stack terraform -Phase 02 -Action plan -Command "terraform -chdir=infra/envs/dev plan -out=tfplan"
.\scripts\run-logged.ps1 -Stack terraform -Phase 02 -Action apply -Command "terraform -chdir=infra/envs/dev apply tfplan"
```

After apply, update kubeconfig:

```powershell
aws eks update-kubeconfig --name cloud-project-dev --region <region>
kubectl get nodes
```

## Phase 3 — CI

Push to `main` or open a PR. Workflow `.github/workflows/ci.yml` runs tests, pushes
`sha-<sha>` images to ECR, and bumps `k8s/overlays/dev/kustomization.yaml`.

## Phase 4 — ArgoCD

```powershell
.\scripts\run-logged.ps1 -Stack argocd -Phase 04 -Action install -Command "kubectl create namespace argocd; kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml"
.\scripts\run-logged.ps1 -Stack argocd -Phase 04 -Action app -Command "kubectl apply -f k8s/argocd/apps/app-of-apps.yaml"
```

Port-forward the UI: `kubectl -n argocd port-forward svc/argocd-server 8080:443`

## Phase 5 — Monitoring

```powershell
.\scripts\run-logged.ps1 -Stack monitoring -Phase 05 -Action install -Command "helm repo add prometheus-community https://prometheus-community.github.io/helm-charts; helm repo update; helm upgrade --install prometheus prometheus-community/kube-prometheus-stack -n monitoring --create-namespace -f monitoring/prometheus/values.yaml"
.\scripts\run-logged.ps1 -Stack monitoring -Phase 05 -Action port-forward -Command "kubectl -n monitoring port-forward svc/prometheus-grafana 3000:80"
```

## Teardown (avoid AWS charges)

```powershell
.\scripts\run-logged.ps1 -Stack terraform -Phase 02 -Action destroy -Command "terraform -chdir=infra/envs/dev destroy -auto-approve"
```

Destroy the EKS environment before the bootstrap bucket. Delete any remaining ELBs/ENIs and
EBS volumes created by Kubernetes, then remove the S3 bucket and DynamoDB table.
