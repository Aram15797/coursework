import re
import time
from typing import Any

from sqlalchemy import event
from sqlalchemy.engine import Engine

from app.core.db_logger import QueryLogEntry, query_context


_TABLE_PATTERNS = [
    re.compile(r"\bfrom\s+\"?([a-zA-Z_][a-zA-Z0-9_]*)\"?", re.IGNORECASE),
    re.compile(r"\bjoin\s+\"?([a-zA-Z_][a-zA-Z0-9_]*)\"?", re.IGNORECASE),
    re.compile(r"\binto\s+\"?([a-zA-Z_][a-zA-Z0-9_]*)\"?", re.IGNORECASE),
    re.compile(r"\bupdate\s+\"?([a-zA-Z_][a-zA-Z0-9_]*)\"?", re.IGNORECASE),
    re.compile(r"\bdelete\s+from\s+\"?([a-zA-Z_][a-zA-Z0-9_]*)\"?", re.IGNORECASE),
]


def _detect_operation(sql: str) -> str:
    stripped = sql.lstrip().lstrip("(").upper()
    for op in ("SELECT", "INSERT", "UPDATE", "DELETE"):
        if stripped.startswith(op):
            return op
    if stripped.startswith("WITH"):
        return "SELECT"
    return "OTHER"


def _extract_tables(sql: str) -> list[str]:
    tables: set[str] = set()
    for pattern in _TABLE_PATTERNS:
        for match in pattern.findall(sql):
            tables.add(match)
    return sorted(tables)


def register_query_listeners(sync_engine: Engine) -> None:
    @event.listens_for(sync_engine, "before_cursor_execute")
    def _before_cursor_execute(  # type: ignore[no-untyped-def]
        conn: Any, cursor: Any, statement: str, parameters: Any, context: Any, executemany: bool
    ) -> None:
        context._query_start_time = time.perf_counter()

    @event.listens_for(sync_engine, "after_cursor_execute")
    def _after_cursor_execute(  # type: ignore[no-untyped-def]
        conn: Any, cursor: Any, statement: str, parameters: Any, context: Any, executemany: bool
    ) -> None:
        ctx = query_context.get()
        if ctx is None:
            return
        start = getattr(context, "_query_start_time", None)
        duration_ms = (time.perf_counter() - start) * 1000.0 if start else 0.0
        try:
            row_count = cursor.rowcount if cursor.rowcount is not None else None
        except Exception:
            row_count = None
        operation = _detect_operation(statement)
        tables = _extract_tables(statement)
        param_repr = None
        try:
            if parameters is not None:
                param_repr = str(parameters)[:300]
        except Exception:
            param_repr = None
        entry = QueryLogEntry(
            sql=statement.strip(),
            operation=operation,
            tables=tables,
            duration_ms=round(duration_ms, 3),
            row_count=row_count if row_count is not None and row_count >= 0 else None,
            parameters=param_repr,
        )
        ctx.add(entry)
