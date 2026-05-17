from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.task import TaskPriority, TaskStatus
from app.schemas.user import UserPublic


class TagRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    color: str


class TagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    color: str = Field(default="#888888", max_length=16)


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.backlog
    priority: TaskPriority = TaskPriority.medium
    assignee_id: Optional[UUID] = None
    parent_task_id: Optional[UUID] = None
    estimated_hours: Optional[Decimal] = None
    due_date: Optional[date] = None
    tag_ids: List[UUID] = []


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    assignee_id: Optional[UUID] = None
    estimated_hours: Optional[Decimal] = None
    logged_hours: Optional[Decimal] = None
    due_date: Optional[date] = None
    tag_ids: Optional[List[UUID]] = None


class TaskMove(BaseModel):
    status: TaskStatus
    position: int = 0


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: Optional[str]
    status: TaskStatus
    priority: TaskPriority
    project_id: UUID
    assignee: Optional[UserPublic]
    reporter: UserPublic
    parent_task_id: Optional[UUID]
    estimated_hours: Optional[Decimal]
    logged_hours: Optional[Decimal]
    due_date: Optional[date]
    position: int
    tags: List[TagRead] = []
    created_at: datetime
    updated_at: datetime


class TaskDetail(TaskRead):
    subtasks: List["TaskRead"] = []
