from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.user import UserPublic


class CommentCreate(BaseModel):
    content: str = Field(min_length=1)
    parent_comment_id: Optional[UUID] = None


class CommentUpdate(BaseModel):
    content: str = Field(min_length=1)


class CommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    content: str
    task_id: UUID
    author: UserPublic
    parent_comment_id: Optional[UUID]
    is_edited: bool
    created_at: datetime
    updated_at: datetime
    replies: List["CommentRead"] = []


CommentRead.model_rebuild()
