from app.core.db_logger import QueryLogEntry, RequestQueryContext
from app.db.events import _detect_operation, _extract_tables


def test_detect_operation():
    assert _detect_operation("SELECT * FROM users") == "SELECT"
    assert _detect_operation("  insert into projects values (1)") == "INSERT"
    assert _detect_operation("UPDATE tasks SET status='done'") == "UPDATE"
    assert _detect_operation("DELETE FROM tags WHERE id = 1") == "DELETE"
    assert _detect_operation("WITH cte AS (SELECT 1) SELECT * FROM cte") == "SELECT"


def test_extract_tables():
    tables = _extract_tables(
        "SELECT u.* FROM users u JOIN projects p ON u.id = p.owner_id"
    )
    assert "users" in tables
    assert "projects" in tables


def test_context_aggregation():
    ctx = RequestQueryContext(method="GET", path="/api/test")
    for i in range(5):
        ctx.add(
            QueryLogEntry(
                sql="SELECT 1 FROM users WHERE id = 1",
                operation="SELECT",
                tables=["users"],
                duration_ms=2.0,
                row_count=1,
            )
        )
    assert ctx.query_count == 5
    assert ctx.total_duration_ms == 10.0
    assert len(ctx.n_plus_one_warnings) == 1
