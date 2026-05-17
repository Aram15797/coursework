import base64
import json
from dataclasses import asdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.db_logger import RequestQueryContext, query_context, remember_context


class QueryInterceptorMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        ctx = RequestQueryContext(method=request.method, path=request.url.path)
        token = query_context.set(ctx)
        try:
            response: Response = await call_next(request)
        finally:
            query_context.reset(token)

        remember_context(ctx)

        summary = {
            "request_id": ctx.request_id,
            "method": ctx.method,
            "path": ctx.path,
            "query_count": ctx.query_count,
            "total_duration_ms": round(ctx.total_duration_ms, 3),
            "n_plus_one_warnings": ctx.n_plus_one_warnings,
            "queries": [asdict(q) for q in ctx.queries],
        }
        encoded = base64.b64encode(json.dumps(summary, default=str).encode()).decode()
        response.headers["X-DB-Request-Id"] = ctx.request_id
        response.headers["X-DB-Query-Count"] = str(ctx.query_count)
        response.headers["X-DB-Query-Duration"] = str(round(ctx.total_duration_ms, 3))
        if len(encoded) < 60000:
            response.headers["X-DB-Query-Log"] = encoded
        response.headers["Access-Control-Expose-Headers"] = (
            "X-DB-Request-Id, X-DB-Query-Count, X-DB-Query-Duration, X-DB-Query-Log"
        )
        return response
