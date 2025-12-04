# Implementation Plan for Kalshi Agent Early Access

This plan tracks the new watchlist/risk/entitlement features. File-level notes show where code will be added or modified.

## Backend
- `backend/app/models/enums.py`: add enums for access/status/kill states and decision reason codes used across the API and risk engine.
- `backend/app/models/schemas.py`: extend ORM models with baseline markets, market access, watchlists, overrides, rules, alerts, pnl ledger, day state, decision receipts, and market requests.
- `backend/app/models/migrations/0001_initial.py`: Alembic-style migration to create the new tables; paired with a simple migration runner.
- `backend/app/models/migrations/__init__.py`: helper for running migrations from code/tests.
- `backend/app/core/risk_engine.py`: implement `risk_gate` with caps, hysteresis, and STOP ONLY behavior plus helper aggregation functions.
- `backend/app/core/watchlist.py`: service helpers for tracking/untracking markets, computing expiry, merging overrides, and fetching watchlist payloads.
- `backend/app/core/tasks.py`: background jobs for watchlist expiry cleanup and heartbeat reconcile that emits decision receipts.
- `backend/app/api/endpoints/watchlist.py`: REST endpoints for watchlist list/add/remove, overrides CRUD, and decision trace access.
- `backend/app/api/endpoints/rules.py`: endpoints for global user rule defaults.
- `backend/app/api/endpoints/admin.py`: baseline seeder endpoint and market request moderation actions.
- `backend/app/api/endpoints/market_requests.py`: endpoint to submit new market requests.
- `backend/app/api/endpoints/markets.py`: extend response to include access status and trackability guard.
- `backend/app/main.py`: wire new routers and start background tasks during lifespan.
- `backend/app/utils/config.py`: introduce trading mode and heartbeat tunables.
- `backend/tests/test_risk_engine.py`: unit tests for soft/hard gate hysteresis and caps.
- `backend/tests/test_watchlist_expiry.py`: validate expiry computation and cleanup logic.
- `backend/tests/test_override_merge.py`: ensure effective rule merge follows override-null semantics.

## Frontend
- `frontend/src/services/api.ts`: add methods for new endpoints (watchlist, overrides, rules, decision traces, market access, seeding, requests).
- `frontend/src/types/index.ts`: define TypeScript types for new resources (watchlist entry, overrides, decision trace, rule defaults, entitlements snapshot).
- `frontend/src/components/Layout.tsx`: update navigation to expose Markets, Watchlist, and Alerts settings aligned with early-access tiers.
- `frontend/src/components/Markets.tsx`: new page with search/filter, track button (or access request), and no overrides per spec.
- `frontend/src/components/Watchlist.tsx`: new watchlist page showing tracked markets, expiry countdown, override drawer with inherit/custom toggles, decision trace line, and tracked count cap indicator.
- `frontend/src/components/AlertsSettings.tsx`: page for global defaults plus tier gating cues.
- `frontend/src/App.css`: light styling additions for override drawer and trace badges.

## Operations
- `README.md`: add concise run/test instructions including migration runner and background job notes.

