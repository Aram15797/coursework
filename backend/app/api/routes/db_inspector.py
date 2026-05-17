from dataclasses import asdict
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session
from app.core.db_logger import get_context, list_recent_contexts
from app.models.user import User, UserRole


router = APIRouter(prefix="/db", tags=["db-inspector"])


def _require_inspector_access(user: User) -> None:
    if user.role not in (UserRole.superadmin, UserRole.admin):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")


@router.get("/schema")
async def get_schema(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    _require_inspector_access(current_user)

    columns_sql = text(
        """
        SELECT table_name, column_name, data_type, is_nullable, column_default,
               character_maximum_length
        FROM information_schema.columns
        WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position
        """
    )
    constraints_sql = text(
        """
        SELECT tc.constraint_name, tc.table_name, tc.constraint_type,
               kcu.column_name,
               ccu.table_name AS foreign_table_name,
               ccu.column_name AS foreign_column_name
        FROM information_schema.table_constraints tc
        LEFT JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
        LEFT JOIN information_schema.constraint_column_usage ccu
          ON ccu.constraint_name = tc.constraint_name AND ccu.table_schema = tc.table_schema
        WHERE tc.table_schema = 'public'
        """
    )

    columns_rows = (await session.execute(columns_sql)).all()
    constraint_rows = (await session.execute(constraints_sql)).all()

    tables: Dict[str, Dict[str, Any]] = {}
    for row in columns_rows:
        t = row.table_name
        tables.setdefault(
            t, {"name": t, "columns": [], "primary_key": [], "foreign_keys": [], "unique": []}
        )
        tables[t]["columns"].append(
            {
                "name": row.column_name,
                "type": row.data_type,
                "nullable": row.is_nullable == "YES",
                "default": row.column_default,
                "max_length": row.character_maximum_length,
            }
        )

    for row in constraint_rows:
        t = row.table_name
        if t not in tables:
            continue
        if row.constraint_type == "PRIMARY KEY":
            if row.column_name and row.column_name not in tables[t]["primary_key"]:
                tables[t]["primary_key"].append(row.column_name)
        elif row.constraint_type == "FOREIGN KEY":
            tables[t]["foreign_keys"].append(
                {
                    "column": row.column_name,
                    "references_table": row.foreign_table_name,
                    "references_column": row.foreign_column_name,
                    "name": row.constraint_name,
                }
            )
        elif row.constraint_type == "UNIQUE":
            if row.column_name and row.column_name not in tables[t]["unique"]:
                tables[t]["unique"].append(row.column_name)

    return {"tables": list(tables.values())}


@router.get("/indexes")
async def get_indexes(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    _require_inspector_access(current_user)
    sql = text(
        """
        SELECT schemaname, tablename, indexname, indexdef
        FROM pg_indexes
        WHERE schemaname = 'public'
        ORDER BY tablename, indexname
        """
    )
    rows = (await session.execute(sql)).all()
    return {
        "indexes": [
            {
                "schema": r.schemaname,
                "table": r.tablename,
                "name": r.indexname,
                "definition": r.indexdef,
            }
            for r in rows
        ]
    }


@router.get("/stats")
async def get_stats(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    _require_inspector_access(current_user)
    sql = text(
        """
        SELECT relname AS table_name,
               n_live_tup AS row_count,
               n_dead_tup AS dead_rows,
               seq_scan, idx_scan,
               pg_size_pretty(pg_total_relation_size(relid)) AS total_size,
               pg_total_relation_size(relid) AS size_bytes
        FROM pg_stat_user_tables
        ORDER BY n_live_tup DESC
        """
    )
    rows = (await session.execute(sql)).all()
    return {
        "tables": [
            {
                "table_name": r.table_name,
                "row_count": r.row_count,
                "dead_rows": r.dead_rows,
                "seq_scan": r.seq_scan,
                "idx_scan": r.idx_scan,
                "total_size": r.total_size,
                "size_bytes": r.size_bytes,
            }
            for r in rows
        ]
    }


@router.get("/query-log/{request_id}")
async def get_query_log(
    request_id: str,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    _require_inspector_access(current_user)
    ctx = get_context(request_id)
    if not ctx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Log not found")
    return {
        "request_id": ctx.request_id,
        "method": ctx.method,
        "path": ctx.path,
        "query_count": ctx.query_count,
        "total_duration_ms": round(ctx.total_duration_ms, 3),
        "n_plus_one_warnings": ctx.n_plus_one_warnings,
        "queries": [asdict(q) for q in ctx.queries],
    }


@router.get("/query-log")
async def list_query_logs(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    _require_inspector_access(current_user)
    contexts = list_recent_contexts(limit=limit)
    return {
        "logs": [
            {
                "request_id": c.request_id,
                "method": c.method,
                "path": c.path,
                "query_count": c.query_count,
                "total_duration_ms": round(c.total_duration_ms, 3),
            }
            for c in contexts
        ]
    }


@router.post("/explain")
async def explain_query(
    payload: Dict[str, str],
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    _require_inspector_access(current_user)
    sql_query = payload.get("sql", "").strip()
    if not sql_query:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing sql")
    lower = sql_query.lower().lstrip()
    if not lower.startswith(("select", "with")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only SELECT/WITH queries are allowed",
        )
    try:
        result = await session.execute(text(f"EXPLAIN (FORMAT JSON) {sql_query}"))
        plan_rows = result.scalars().all()
        return {"plan": list(plan_rows)}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
