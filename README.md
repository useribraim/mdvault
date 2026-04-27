# Markdown Knowledge Base

A private web-based Markdown knowledge base built around a FastAPI backend and PostgreSQL.

## Step 1: Backend Skeleton

This first step contains:

- FastAPI application factory
- Environment-based configuration
- PostgreSQL SQLAlchemy session setup
- Health endpoint at `GET /health`
- Database health endpoint at `GET /health/db`
- Docker Compose for API + PostgreSQL

## Step 2: Database Foundation

The first schema contains:

- `users` for account identity and password hashes
- `folders` for parent-child note organization
- `notes` for raw Markdown content stored in PostgreSQL
- Alembic migration setup under `backend/alembic`

Notes are stored as Markdown text in `notes.body_markdown`.

## Run Locally

```bash
cp .env.example .env
docker compose up --build
```

Then check:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/health/db
```

## Run Migrations

```bash
docker compose exec api alembic upgrade head
```
