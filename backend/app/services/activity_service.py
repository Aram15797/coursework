from typing import Any, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity import ActivityLog


async def record_activity(
    session: AsyncSession,
    *,
    entity_type: str,
    entity_id: UUID,
    action: str,
    user_id: Optional[UUID],
    old_values: Optional[dict[str, Any]] = None,
    new_values: Optional[dict[str, Any]] = None,
) -> None:
    log = ActivityLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        user_id=user_id,
        old_values=old_values,
        new_values=new_values,
    )
    session.add(log)
