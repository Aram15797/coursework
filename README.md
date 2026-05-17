# PTMS — Project & Task Management System

A full-stack project & task management system with a built-in **Database Visualization Layer**: every API response carries the SQL queries that produced it, and an admin-only Schema Explorer renders an interactive ER diagram of the live PostgreSQL schema with table statistics and indexes.

This is a coursework project for the **Databases** discipline.

---

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│   Browser   │ ──► │    Nginx     │ ──► │  React (Vite)│
│             │     │ reverse-proxy│     │   :5173      │
└─────────────┘     │   :80        │     └──────────────┘
                    │              │     ┌──────────────┐
                    │              │ ──► │ FastAPI :8000│
                    └──────────────┘     │  + SQLAlchemy│
                                         │  + Alembic   │
                                         └──────┬───────┘
                                                │
                                         ┌──────▼───────┐   ┌─────────┐
                                         │ PostgreSQL 16│   │ Redis 7 │
                                         │    :5432     │   │  :6379  │
                                         └──────────────┘   └─────────┘
```

- **Backend**: Python 3.11, FastAPI, SQLAlchemy 2 (async), Alembic, asyncpg, Pydantic v2, JWT, bcrypt
- **Frontend**: React 18, TypeScript, Vite, TanStack Query, Zustand, React Router, Tailwind CSS, Recharts, React Flow, Prism.js
- **Infra**: Docker Compose, Nginx reverse-proxy

---

## Quick start

```bash
cp .env.example .env
docker compose up --build
```

Then open:

| URL | Purpose |
|---|---|
| http://localhost          | Web UI (through Nginx) |
| http://localhost:5173     | Direct Vite dev server |
| http://localhost:8000/api/docs | Swagger UI |
| http://localhost:8000/api/redoc | ReDoc |

The first start automatically:
1. Runs Alembic migrations (`alembic upgrade head`).
2. Seeds the database with demo users, projects, tasks, comments, and tags (`python -m app.seed`).

### Demo accounts

| Email | Password | Role |
|---|---|---|
| `admin@example.com` | `admin123` | superadmin |
| `alice@example.com` | `alice123` | manager |
| `bob@example.com`   | `bob123`   | member |
| `carol@example.com` | `carol123` | member |

---

## Project structure

```
.
├── backend/
│   ├── app/
│   │   ├── api/routes/      # auth, users, projects, tasks, comments, dashboard, db_inspector
│   │   ├── core/            # config, security, db_logger (query context)
│   │   ├── db/              # SQLAlchemy engine + event listeners (SQL interception)
│   │   ├── models/          # User, Project, Task, Tag, Comment, ActivityLog
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── middleware/      # QueryInterceptorMiddleware
│   │   ├── services/        # activity logging
│   │   ├── seed.py          # demo data
│   │   └── main.py
│   ├── alembic/             # migrations (initial schema in 0001_initial.py)
│   ├── tests/               # pytest unit tests
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── api/             # axios client + endpoint helpers
│       ├── components/
│       │   ├── layout/      # AppLayout, ProtectedRoute
│       │   └── db-inspector/# InspectorPanel, InspectorToggle
│       ├── pages/           # Dashboard, Projects, ProjectDetail, TaskDetail, DbExplorer, Login, Register
│       ├── store/           # zustand stores (auth, inspector)
│       └── types/
├── nginx/nginx.conf
├── docker-compose.yml
└── .env.example
```

---

## DB Visualization Layer

### 1. Inline Query Log (every request)

A `QueryInterceptorMiddleware` sets a per-request `ContextVar` and listens to SQLAlchemy's `before_cursor_execute` / `after_cursor_execute` engine events. Every executed SQL statement is captured with:

- the SQL text,
- detected operation (SELECT / INSERT / UPDATE / DELETE),
- referenced tables (regex-parsed from the statement),
- duration in ms,
- affected/returned row count,
- bound parameters.

The aggregated log is serialized to base64 JSON and attached to each response as the `X-DB-Query-Log` header (alongside `X-DB-Request-Id`, `X-DB-Query-Count`, `X-DB-Query-Duration`).

On the frontend, the global axios response interceptor decodes the header and pushes the log into a Zustand store. A bottom panel ("DB Inspector") shows:

- a list of the last 100 requests,
- per-request stats (count, total ms, N+1 warnings),
- a Recharts bar chart of per-query timings,
- each query with Prism-highlighted SQL, operation badge, table chips and bound parameters.

Toggle it with the **"DB Inspector"** button in the header.

### 2. Schema Explorer (`/db-explorer`, admin-only)

A separate page renders the live database schema as an interactive **React Flow** ER diagram. Nodes are tables (columns + types, PK/FK markers); edges are foreign-key relations.

Data sources (queried via `information_schema` and `pg_catalog`):

| Endpoint | What it returns |
|---|---|
| `GET /api/db/schema`  | tables, columns, primary keys, foreign keys, unique constraints |
| `GET /api/db/indexes` | `pg_indexes` definitions for all public tables |
| `GET /api/db/stats`   | `pg_stat_user_tables` row counts, seq/idx scans, table size |
| `GET /api/db/query-log/{request_id}` | full captured log of a specific HTTP request |
| `POST /api/db/explain` | `EXPLAIN (FORMAT JSON)` for an ad-hoc SELECT |

Clicking a table opens a side panel with its columns, primary key, foreign keys, indexes, and live statistics.

---

## API overview

```
POST   /api/auth/register
POST   /api/auth/login
POST   /api/auth/refresh
POST   /api/auth/logout

GET    /api/users/me
PATCH  /api/users/me
POST   /api/users/me/password
GET    /api/users

GET    /api/projects
POST   /api/projects
GET    /api/projects/{id}
PATCH  /api/projects/{id}
DELETE /api/projects/{id}
POST   /api/projects/{id}/members
DELETE /api/projects/{id}/members/{user_id}

GET    /api/projects/{id}/tasks
POST   /api/projects/{id}/tasks
GET    /api/tasks/{id}
PATCH  /api/tasks/{id}
DELETE /api/tasks/{id}
PATCH  /api/tasks/{id}/move

GET    /api/tasks/{id}/comments
POST   /api/tasks/{id}/comments
PATCH  /api/comments/{id}
DELETE /api/comments/{id}

GET    /api/tags
POST   /api/tags

GET    /api/dashboard/my-tasks
GET    /api/dashboard/stats
GET    /api/dashboard/activity

GET    /api/db/schema
GET    /api/db/indexes
GET    /api/db/stats
GET    /api/db/query-log/{request_id}
GET    /api/db/query-log
POST   /api/db/explain
```

Full interactive docs are auto-generated at **`/api/docs`** (Swagger) and **`/api/redoc`**.

---

## Database schema

10 tables:

```
users (UUID id, email/username UNIQUE, role ENUM, …)
projects (owner_id → users)
project_members (project_id, user_id, role ENUM)        -- m2m
tasks (project_id, assignee_id, reporter_id, parent_task_id, status, priority, position)
tags (name UNIQUE, color)
task_tags (task_id, tag_id)                              -- m2m
comments (task_id, author_id, parent_comment_id)         -- self-referencing threads
activity_log (entity_type, entity_id, action, old/new JSONB)
```

Mandatory indexes (created by migration `0001_initial`):
`idx_tasks_project_id`, `idx_tasks_assignee_id`, `idx_tasks_status`, `idx_tasks_due_date`,
`idx_comments_task_id`, `idx_activity_log_entity`, `idx_activity_log_user`.

---

## Running tests

```bash
cd backend
pip install -r requirements.txt
pytest
```

The included pytest suite covers password hashing, JWT round-trips, schema validation, and the SQL parsing helpers used by the query interceptor.

---

## Development tips

- Hot-reload is enabled for both the backend (`uvicorn --reload`) and the frontend (Vite). Source folders are bind-mounted in `docker-compose.yml`.
- To regenerate migrations after changing models:
  ```bash
  docker compose exec backend alembic revision --autogenerate -m "your message"
  docker compose exec backend alembic upgrade head
  ```
- To wipe everything (including DB volume): `docker compose down -v`.

---

## License

MIT.
