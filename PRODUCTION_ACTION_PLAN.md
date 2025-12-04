# Production Action Plan

This plan operationalizes the outstanding readiness items so the Kalshi Probability Analysis Agent can be deployed safely to production.

## 1) Database migrations and backups
- **Disable auto-provisioning in production:** `AUTO_CREATE_TABLES` now defaults to `false`; keep it that way in production so schema changes are handled by migrations instead of application startup.
- **Create an Alembic migration project:**
  ```bash
  cd backend
  poetry run alembic init migrations  # or `pip install alembic` if poetry is not used
  ```
  Configure `env.py` to import `Base` from `app.models.database` and set `target_metadata = Base.metadata`.
- **Generate and apply migrations:**
  ```bash
  cd backend
  alembic revision --autogenerate -m "initial schema"
  alembic upgrade head
  ```
  Run these commands as part of every release pipeline before starting the application pods/containers.
- **Backups:** take nightly logical backups and pre-deploy snapshots:
  ```bash
  pg_dump "$DATABASE_URL" > "backups/kalshi_$(date +%F).sql"
  ```
  Store backups in off-host storage and rehearse restores in a staging environment.

## 2) Tighten CORS for production
- **Whitelist only trusted origins:** set `CORS_ORIGINS` to the production domains (e.g., `https://app.example.com,https://admin.example.com`). Wildcards (`*`) are blocked by validation and should not be used.
- **Rebuild/redeploy after updates:** any change to CORS configuration requires redeploying the backend to load the new settings.

## 3) Logging retention and shipping
- **Rotation defaults:** application logs rotate daily and retain 30 days; error logs rotate weekly and retain 90 days. Ensure the `logs/` directory is writable in your container/host.
- **Centralize logs:** ship `logs/app.log*` and `logs/app_error.log*` to your logging stack (e.g., Loki, CloudWatch, or ELK) with matching retention rules.
- **Confirm policy coverage:** verify platform-level log retention/backup policies align with the above windows and audit access to the log storage location.
