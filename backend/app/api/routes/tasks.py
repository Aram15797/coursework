from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_session
from app.api.routes.projects import (
    _user_can_access_project,
    _user_can_manage_project,
)
from app.models.tag import Tag
from app.models.task import Task, TaskPriority, TaskStatus
from app.models.user import User
from app.schemas.task import (
    TagCreate,
    TagRead,
    TaskCreate,
    TaskDetail,
    TaskMove,
    TaskRead,
    TaskUpdate,
)
from app.services.activity_service import record_activity


router = APIRouter(tags=["tasks"])


def _task_load_options():
    return [
        selectinload(Task.assignee),
        selectinload(Task.reporter),
        selectinload(Task.tags),
    ]


async def _get_task_or_404(session: AsyncSession, task_id: UUID) -> Task:
    result = await session.execute(
        select(Task).options(*_task_load_options()).where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


@router.get("/projects/{project_id}/tasks", response_model=List[TaskRead])
async def list_project_tasks(
    project_id: UUID,
    status_filter: Optional[TaskStatus] = Query(default=None, alias="status"),
    assignee_id: Optional[UUID] = None,
    priority: Optional[TaskPriority] = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> List[Task]:
    project = await _user_can_access_project(session, project_id, current_user)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    query = (
        select(Task)
        .options(*_task_load_options())
        .where(Task.project_id == project_id)
        .order_by(Task.position.asc(), Task.created_at.desc())
    )
    if status_filter:
        query = query.where(Task.status == status_filter)
    if assignee_id:
        query = query.where(Task.assignee_id == assignee_id)
    if priority:
        query = query.where(Task.priority == priority)
    result = await session.execute(query)
    return list(result.scalars().all())


@router.post(
    "/projects/{project_id}/tasks", response_model=TaskRead, status_code=status.HTTP_201_CREATED
)
async def create_task(
    project_id: UUID,
    payload: TaskCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Task:
    project = await _user_can_access_project(session, project_id, current_user)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    task = Task(
        title=payload.title,
        description=payload.description,
        status=payload.status,
        priority=payload.priority,
        project_id=project_id,
        assignee_id=payload.assignee_id,
        reporter_id=current_user.id,
        parent_task_id=payload.parent_task_id,
        estimated_hours=payload.estimated_hours,
        due_date=payload.due_date,
    )
    if payload.tag_ids:
        tag_result = await session.execute(select(Tag).where(Tag.id.in_(payload.tag_ids)))
        task.tags = list(tag_result.scalars().all())
    session.add(task)
    await session.flush()
    await record_activity(
        session,
        entity_type="task",
        entity_id=task.id,
        action="created",
        user_id=current_user.id,
        new_values={"title": task.title, "status": task.status.value},
    )
    await session.commit()

    return await _get_task_or_404(session, task.id)


@router.get("/tasks/{task_id}", response_model=TaskDetail)
async def get_task(
    task_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> TaskDetail:
    task = await _get_task_or_404(session, task_id)
    project = await _user_can_access_project(session, task.project_id, current_user)
    if not project:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    subtasks_result = await session.execute(
        select(Task)
        .options(*_task_load_options())
        .where(Task.parent_task_id == task_id)
        .order_by(Task.created_at.asc())
    )
    subtasks = list(subtasks_result.scalars().all())
    base = TaskRead.model_validate(task)
    detail = TaskDetail(
        **base.model_dump(),
        subtasks=[TaskRead.model_validate(st) for st in subtasks],
    )
    return detail


@router.patch("/tasks/{task_id}", response_model=TaskRead)
async def update_task(
    task_id: UUID,
    payload: TaskUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Task:
    task = await _get_task_or_404(session, task_id)
    project = await _user_can_access_project(session, task.project_id, current_user)
    if not project:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    data = payload.model_dump(exclude_unset=True)
    tag_ids = data.pop("tag_ids", None)
    old_status = task.status.value
    for field, value in data.items():
        setattr(task, field, value)
    if tag_ids is not None:
        tag_result = await session.execute(select(Tag).where(Tag.id.in_(tag_ids)))
        task.tags = list(tag_result.scalars().all())

    await record_activity(
        session,
        entity_type="task",
        entity_id=task.id,
        action="updated",
        user_id=current_user.id,
        old_values={"status": old_status},
        new_values=payload.model_dump(exclude_unset=True, mode="json"),
    )
    await session.commit()
    return await _get_task_or_404(session, task.id)


@router.patch("/tasks/{task_id}/move", response_model=TaskRead)
async def move_task(
    task_id: UUID,
    payload: TaskMove,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Task:
    task = await _get_task_or_404(session, task_id)
    project = await _user_can_access_project(session, task.project_id, current_user)
    if not project:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    old_status = task.status
    task.status = payload.status
    task.position = payload.position
    await record_activity(
        session,
        entity_type="task",
        entity_id=task.id,
        action="moved",
        user_id=current_user.id,
        old_values={"status": old_status.value},
        new_values={"status": payload.status.value, "position": payload.position},
    )
    await session.commit()
    return await _get_task_or_404(session, task.id)


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> None:
    task = await _get_task_or_404(session, task_id)
    project = await _user_can_manage_project(session, task.project_id, current_user)
    if not project:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    await session.delete(task)
    await session.commit()


@router.get("/tags", response_model=List[TagRead])
async def list_tags(
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
) -> List[Tag]:
    result = await session.execute(select(Tag).order_by(Tag.name))
    return list(result.scalars().all())


@router.post("/tags", response_model=TagRead, status_code=status.HTTP_201_CREATED)
async def create_tag(
    payload: TagCreate,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
) -> Tag:
    existing = await session.execute(select(Tag).where(Tag.name == payload.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tag exists")
    tag = Tag(name=payload.name, color=payload.color)
    session.add(tag)
    await session.commit()
    await session.refresh(tag)
    return tag
