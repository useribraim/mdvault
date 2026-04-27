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

## Step 3: Authentication Foundation

The first auth slice contains:

- `POST /auth/register` to create an account
- `POST /auth/login` to return a bearer access token
- `GET /me` to return the authenticated user
- Argon2 password hashing
- JWT access tokens

## Step 4: Notes CRUD

Authenticated users can now manage their own Markdown notes:

- `POST /notes` creates a note
- `GET /notes` lists the current user's active notes
- `GET /notes/{note_id}` reads one note
- `PATCH /notes/{note_id}` updates title, Markdown body, or folder
- `DELETE /notes/{note_id}` soft-deletes a note

Each notes endpoint is scoped to the authenticated user.

## Step 5: Folders

Authenticated users can organize notes with folders:

- `POST /folders` creates a folder
- `GET /folders` lists the current user's folders
- `GET /folders/{folder_id}` reads one folder
- `PATCH /folders/{folder_id}` updates name or parent folder
- `DELETE /folders/{folder_id}` deletes a folder while preserving notes

Folder parent relationships are scoped to the current user and cannot form cycles.

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

Auth check:

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"strong-password"}'
```

Create a note after authorizing in Swagger UI or by sending a bearer token:

```bash
curl -X POST http://localhost:8000/notes \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{"title":"First note","body_markdown":"# Hello"}'
```

## Run Migrations

```bash
docker compose exec api alembic upgrade head
```
