from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.project import ProjectMemberRole, ProjectPriority, ProjectStatus
from app.schemas.user import UserPublic


class ProjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    status: ProjectStatus = ProjectStatus.planning
    priority: ProjectPriority = ProjectPriority.medium
    start_date: Optional[date] = None
    due_date: Optional[date] = None


class ProjectUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[ProjectStatus] = None
    priority: Optional[ProjectPriority] = None
    start_date: Optional[date] = None
    due_date: Optional[date] = None


class ProjectMemberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user: UserPublic
    role: ProjectMemberRole
    joined_at: datetime


class ProjectMemberAdd(BaseModel):
    user_id: UUID
    role: ProjectMemberRole = ProjectMemberRole.member


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: Optional[str]
    status: ProjectStatus
    priority: ProjectPriority
    owner: UserPublic
    start_date: Optional[date]
    due_date: Optional[date]
    created_at: datetime
    updated_at: datetime


class ProjectDetail(ProjectRead):
    members: List[ProjectMemberRead] = []
    task_count: int = 0
    completed_task_count: int = 0
    progress: float = 0.0
