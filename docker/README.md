# Local Docker Environment

Runs Postgres, the FastAPI backend, and the React frontend.

```powershell
# 1. Create environment file
Copy-Item docker/.env.example docker/.env

# 2. Build and start everything
.\scripts\run-logged.ps1 -Stack docker -Phase 01 -Action up `
  -Command "docker compose -f docker/docker-compose.yml up -d --build"

# 3. Check status / logs
docker compose -f docker/docker-compose.yml ps
docker compose -f docker/docker-compose.yml logs -f backend

# 4. Stop (keep data)
docker compose -f docker/docker-compose.yml down

# 5. Stop and delete database volume (reloads seed next start)
docker compose -f docker/docker-compose.yml down -v
```

| Service  | URL |
| -------- | --- |
| Frontend | http://localhost:8080 |
| API docs | http://localhost:8000/docs |
| Health   | http://localhost:8000/api/health |

Sign in with `ADMIN_EMAIL` / `ADMIN_PASSWORD` from `docker/.env`.

The seed CSVs in `app/db/seed/` load only on first database initialization.
After changing seeds, run `down -v` before `up` again.

Backend logs are written to `logs/backend/` and `logs/combined/` (bind-mounted).
