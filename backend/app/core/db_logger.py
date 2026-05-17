from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import List, Optional
from uuid import uuid4


@dataclass
class QueryLogEntry:
    sql: str
    operation: str
    tables: List[str]
    duration_ms: float
    row_count: Optional[int]
    parameters: Optional[str] = None
    explain: Optional[str] = None


@dataclass
class RequestQueryContext:
    request_id: str = field(default_factory=lambda: str(uuid4()))
    queries: List[QueryLogEntry] = field(default_factory=list)
    method: str = ""
    path: str = ""

    def add(self, entry: QueryLogEntry) -> None:
        self.queries.append(entry)

    @property
    def total_duration_ms(self) -> float:
        return sum(q.duration_ms for q in self.queries)

    @property
    def query_count(self) -> int:
        return len(self.queries)

    @property
    def n_plus_one_warnings(self) -> List[str]:
        warnings: List[str] = []
        select_signatures: dict[str, int] = {}
        for entry in self.queries:
            if entry.operation == "SELECT":
                normalized = " ".join(entry.sql.lower().split())[:120]
                select_signatures[normalized] = select_signatures.get(normalized, 0) + 1
        for signature, count in select_signatures.items():
            if count >= 4:
                warnings.append(f"Possible N+1: {count} similar SELECT queries")
        return warnings


query_context: ContextVar[Optional[RequestQueryContext]] = ContextVar(
    "query_context", default=None
)


_history_store: dict[str, RequestQueryContext] = {}
_history_order: List[str] = []
_HISTORY_LIMIT = 200


def remember_context(ctx: RequestQueryContext) -> None:
    _history_store[ctx.request_id] = ctx
    _history_order.append(ctx.request_id)
    while len(_history_order) > _HISTORY_LIMIT:
        oldest = _history_order.pop(0)
        _history_store.pop(oldest, None)


def get_context(request_id: str) -> Optional[RequestQueryContext]:
    return _history_store.get(request_id)


def list_recent_contexts(limit: int = 50) -> List[RequestQueryContext]:
    ids = _history_order[-limit:][::-1]
    return [_history_store[i] for i in ids if i in _history_store]
