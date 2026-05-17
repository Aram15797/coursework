from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_session
from app.models.activity import ActivityLog
from app.models.project import Project, ProjectMember
from app.models.task import Task, TaskStatus
from app.models.user import User, UserRole
from app.schemas.activity import ActivityRead
from app.schemas.task import TaskRead


router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _is_admin(user: User) -> bool:
    return user.role in (UserRole.superadmin, UserRole.admin)


@router.get("/my-tasks", response_model=List[TaskRead])
async def my_tasks(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> List[Task]:
    result = await session.execute(
        select(Task)
        .options(
            selectinload(Task.assignee),
            selectinload(Task.reporter),
            selectinload(Task.tags),
        )
        .where(Task.assignee_id == current_user.id, Task.status != TaskStatus.done)
        .order_by(Task.due_date.asc().nullslast(), Task.created_at.desc())
    )
    return list(result.scalars().all())


async def _accessible_project_ids(session: AsyncSession, user: User) -> list:
    if _is_admin(user):
        result = await session.execute(select(Project.id))
        return list(result.scalars().all())
    member_subq = (
        select(ProjectMember.project_id)
        .where(ProjectMember.user_id == user.id)
        .scalar_subquery()
    )
    result = await session.execute(
        select(Project.id).where(or_(Project.owner_id == user.id, Project.id.in_(member_subq)))
    )
    return list(result.scalars().all())


@router.get("/stats")
async def stats(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    project_ids = await _accessible_project_ids(session, current_user)

    if project_ids:
        task_rows = await session.execute(
            select(Task.status, func.count(Task.id))
            .where(Task.project_id.in_(project_ids))
            .group_by(Task.status)
        )
        project_rows = await session.execute(
            select(Project.priority, func.count(Project.id))
            .where(Project.id.in_(project_ids))
            .group_by(Project.priority)
        )
        tasks_by_status = {s.value: count for s, count in task_rows.all()}
        projects_by_priority = {p.value: count for p, count in project_rows.all()}
    else:
        tasks_by_status = {}
        projects_by_priority = {}

    return {
        "tasks_by_status": tasks_by_status,
        "projects_by_priority": projects_by_priority,
        "total_projects": len(project_ids),
        "total_tasks": sum(tasks_by_status.values()),
    }


@router.get("/activity", response_model=List[ActivityRead])
async def recent_activity(
    limit: int = Query(default=30, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
) -> List[ActivityLog]:
    result = await session.execute(
        select(ActivityLog).order_by(desc(ActivityLog.created_at)).limit(limit)
    )
    return list(result.scalars().all())
