# Run Logs

Every command run for this project is captured here by `scripts/run-logged.ps1`.
Logs are grouped **per tech stack** so concurrent runs never clash.

## Layout

```
logs/
├── combined/    # every event from every stack (single rolling stream)
├── backend/     # Python backend runs (logging_config.py)
├── frontend/    # frontend build/serve logs
├── docker/      # docker, docker compose
├── terraform/   # bootstrap, init, plan, apply, destroy
├── ci/          # GitHub Actions / ECR / manifest bumps
├── argocd/      # ArgoCD install, app sync
└── monitoring/  # Helm installs, port-forwards, alert tests
```

## Two Kinds of Logs

| Kind | Produced by | Path | Purpose |
| ---- | ----------- | ---- | ------- |
| Combined | `app/backend/app/logging_config.py` | `logs/combined/combined.log` | One rolling file with every event from every run |
| Per-stack (shell) | `scripts/run-logged.ps1` | `logs/<stack>/<phase>-<action>-<timestamp>.log` | Raw command output per stack |
| Per-run (Python) | `app/backend/app/logging_config.py` | `logs/<stack>/<stack>-<timestamp>.log` | Application events for one run |

All Python logs are also echoed to the console. Log lines look like:

```
[ 2026-07-27 16:17:41,978 ] httpx - INFO - HTTP Request: GET https://example.com "HTTP/1.1 200 OK"
[ 2026-07-27 16:17:41,989 ] app.main - INFO - backend started
```

## Python Logger

```python
from app.logging_config import configure_logger, get_logger

configure_logger(stack="backend")   # writes combined + logs/backend/<run>.log
logger = get_logger(__name__)
logger.info("ready")
```

Environment overrides: `LOG_STACK`, `LOG_DIR`, `PROJECT_ROOT`. Files rotate at 5 MB with 3 backups.

## Naming Convention

```
<stack>/<phase>-<action>-<yyyyMMdd-HHmmss>.log
```

Examples:

```
logs/docker/01-compose-up-20261110-151000.log
logs/terraform/02-plan-20261110-143200.log
logs/ci/03-ecr-push-run12345.log
logs/argocd/04-sync-20261110-160000.log
logs/monitoring/05-install-20261110-170000.log
```

## Usage

```powershell
.\scripts\run-logged.ps1 -Stack terraform -Phase 02 -Action plan -Command "terraform -chdir=infra/envs/dev plan"
```

Each file starts with a header (timestamp, user, host, stack, command) and ends with the
exit code, making failures easy to spot.

Logs are git-ignored (`.log`), but the folder structure is preserved with `.gitkeep`.
