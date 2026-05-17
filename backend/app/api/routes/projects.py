from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_session
from app.models.project import (
    Project,
    ProjectMember,
    ProjectMemberRole,
    ProjectPriority,
    ProjectStatus,
)
from app.models.task import Task, TaskStatus
from app.models.user import User, UserRole
from app.schemas.project import (
    ProjectCreate,
    ProjectDetail,
    ProjectMemberAdd,
    ProjectMemberRead,
    ProjectRead,
    ProjectUpdate,
)
from app.services.activity_service import record_activity


router = APIRouter(prefix="/projects", tags=["projects"])


async def _user_can_access_project(
    session: AsyncSession, project_id: UUID, user: User
) -> Optional[Project]:
    result = await session.execute(
        select(Project)
        .options(selectinload(Project.owner), selectinload(Project.members).selectinload(ProjectMember.user))
        .where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        return None
    if user.role in (UserRole.superadmin, UserRole.admin):
        return project
    if project.owner_id == user.id:
        return project
    for member in project.members:
        if member.user_id == user.id:
            return project
    return None


async def _user_can_manage_project(
    session: AsyncSession, project_id: UUID, user: User
) -> Optional[Project]:
    project = await _user_can_access_project(session, project_id, user)
    if not project:
        return None
    if user.role in (UserRole.superadmin, UserRole.admin):
        return project
    if project.owner_id == user.id:
        return project
    for member in project.members:
        if member.user_id == user.id and member.role == ProjectMemberRole.manager:
            return project
    return None


@router.get("", response_model=List[ProjectRead])
async def list_projects(
    status_filter: Optional[ProjectStatus] = Query(default=None, alias="status"),
    priority: Optional[ProjectPriority] = None,
    search: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> List[Project]:
    query = select(Project).options(selectinload(Project.owner)).order_by(Project.created_at.desc())

    if current_user.role not in (UserRole.superadmin, UserRole.admin):
        member_subq = (
            select(ProjectMember.project_id)
            .where(ProjectMember.user_id == current_user.id)
            .scalar_subquery()
        )
        query = query.where(
            or_(Project.owner_id == current_user.id, Project.id.in_(member_subq))
        )
    if status_filter:
        query = query.where(Project.status == status_filter)
    if priority:
        query = query.where(Project.priority == priority)
    if search:
        like = f"%{search}%"
        query = query.where(or_(Project.title.ilike(like), Project.description.ilike(like)))

    result = await session.execute(query)
    return list(result.scalars().all())


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Project:
    project = Project(
        title=payload.title,
        description=payload.description,
        status=payload.status,
        priority=payload.priority,
        start_date=payload.start_date,
        due_date=payload.due_date,
        owner_id=current_user.id,
    )
    session.add(project)
    await session.flush()

    session.add(
        ProjectMember(
            project_id=project.id, user_id=current_user.id, role=ProjectMemberRole.manager
        )
    )
    await record_activity(
        session,
        entity_type="project",
        entity_id=project.id,
        action="created",
        user_id=current_user.id,
        new_values={"title": project.title},
    )
    await session.commit()
    await session.refresh(project, attribute_names=["owner"])
    return project


@router.get("/{project_id}", response_model=ProjectDetail)
async def get_project(
    project_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ProjectDetail:
    project = await _user_can_access_project(session, project_id, current_user)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    total = (
        await session.execute(select(func.count(Task.id)).where(Task.project_id == project.id))
    ).scalar_one()
    done = (
        await session.execute(
            select(func.count(Task.id)).where(
                Task.project_id == project.id, Task.status == TaskStatus.done
            )
        )
    ).scalar_one()
    progress = (done / total * 100.0) if total else 0.0

    members_data = [ProjectMemberRead.model_validate(m) for m in project.members]
    detail = ProjectDetail(
        id=project.id,
        title=project.title,
        description=project.description,
        status=project.status,
        priority=project.priority,
        owner=project.owner,  # type: ignore[arg-type]
        start_date=project.start_date,
        due_date=project.due_date,
        created_at=project.created_at,
        updated_at=project.updated_at,
        members=members_data,
        task_count=int(total),
        completed_task_count=int(done),
        progress=round(progress, 2),
    )
    return detail


@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project(
    project_id: UUID,
    payload: ProjectUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Project:
    project = await _user_can_manage_project(session, project_id, current_user)
    if not project:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    old_values = {
        "title": project.title,
        "status": project.status.value,
        "priority": project.priority.value,
    }
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    await record_activity(
        session,
        entity_type="project",
        entity_id=project.id,
        action="updated",
        user_id=current_user.id,
        old_values=old_values,
        new_values=payload.model_dump(exclude_unset=True, mode="json"),
    )
    await session.commit()
    await session.refresh(project, attribute_names=["owner"])
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> None:
    project = await _user_can_manage_project(session, project_id, current_user)
    if not project:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    if project.owner_id != current_user.id and current_user.role not in (
        UserRole.superadmin,
        UserRole.admin,
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only owner can delete")
    await session.delete(project)
    await session.commit()


@router.post(
    "/{project_id}/members", response_model=ProjectMemberRead, status_code=status.HTTP_201_CREATED
)
async def add_member(
    project_id: UUID,
    payload: ProjectMemberAdd,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ProjectMemberRead:
    project = await _user_can_manage_project(session, project_id, current_user)
    if not project:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    existing = await session.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id, ProjectMember.user_id == payload.user_id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Member exists")

    user_check = await session.execute(select(User).where(User.id == payload.user_id))
    user = user_check.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    member = ProjectMember(project_id=project_id, user_id=payload.user_id, role=payload.role)
    session.add(member)
    await session.commit()
    await session.refresh(member, attribute_names=["user"])
    return ProjectMemberRead.model_validate(member)


@router.delete("/{project_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    project_id: UUID,
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> None:
    project = await _user_can_manage_project(session, project_id, current_user)
    if not project:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    if project.owner_id == user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot remove owner")
    result = await session.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id, ProjectMember.user_id == user_id
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    await session.delete(member)
    await session.commit()
