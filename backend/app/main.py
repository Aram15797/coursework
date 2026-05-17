import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import OperationalError

from app.api.routes import (
    auth as auth_routes,
    comments as comment_routes,
    dashboard as dashboard_routes,
    db_inspector as db_routes,
    projects as project_routes,
    tasks as task_routes,
    users as user_routes,
)
from app.core.config import settings
from app.db.events import register_query_listeners
from app.db.session import engine
from app.middleware.query_interceptor import QueryInterceptorMiddleware


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Project & Task Management System",
        description="Course project with built-in DB visualization layer",
        version="1.0.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url="/api/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[
            "X-DB-Request-Id",
            "X-DB-Query-Count",
            "X-DB-Query-Duration",
            "X-DB-Query-Log",
        ],
    )
    app.add_middleware(QueryInterceptorMiddleware)

    api_prefix = "/api"
    app.include_router(auth_routes.router, prefix=api_prefix)
    app.include_router(user_routes.router, prefix=api_prefix)
    app.include_router(project_routes.router, prefix=api_prefix)
    app.include_router(task_routes.router, prefix=api_prefix)
    app.include_router(comment_routes.router, prefix=api_prefix)
    app.include_router(dashboard_routes.router, prefix=api_prefix)
    app.include_router(db_routes.router, prefix=api_prefix)

    @app.get("/api/health")
    async def health() -> dict:
        return {"status": "ok", "environment": settings.environment}

    @app.on_event("startup")
    async def on_startup() -> None:
        for attempt in range(20):
            try:
                async with engine.connect() as conn:
                    sync_engine = conn.sync_connection.engine
                    register_query_listeners(sync_engine)
                logger.info("Database connection established")
                break
            except OperationalError as exc:
                logger.warning("DB not ready (attempt %s): %s", attempt + 1, exc)
                await asyncio.sleep(2)

    return app


app = create_app()
