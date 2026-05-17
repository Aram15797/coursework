from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ActivityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    entity_type: str
    entity_id: UUID
    action: str
    user_id: Optional[UUID]
    old_values: Optional[dict[str, Any]]
    new_values: Optional[dict[str, Any]]
    created_at: datetime
