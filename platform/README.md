# Manga Update Platform (Phase 1)

A greenfield, Docker-first update detector for manga/content sources.

## Phase 1
- Source: CopyManga
- Features: search, one-click subscription, scheduled checks, daily summary
- Channels: Webhook + RSS

## Run locally

```bash
python -m pip install -r backend/requirements.txt
set PYTHONPATH=backend
uvicorn app.main:app --reload --port 8000
```

## Frontend dev

```bash
cd frontend
corepack enable
pnpm install
pnpm dev
```

## Docker

```bash
docker compose up -d --build
```

## CI Entrypoints
- `make ci-backend`
- `make ci-frontend`
- `make ci-build`
- `make ci-integration`
