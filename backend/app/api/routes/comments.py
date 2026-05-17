from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_session
from app.api.routes.projects import _user_can_access_project
from app.models.comment import Comment
from app.models.task import Task
from app.models.user import User
from app.schemas.comment import CommentCreate, CommentRead, CommentUpdate
from app.services.activity_service import record_activity


router = APIRouter(tags=["comments"])


def _comment_options():
    return [selectinload(Comment.author), selectinload(Comment.replies).selectinload(Comment.author)]


def _build_tree(items: List[Comment]) -> List[Comment]:
    by_parent: dict[UUID | None, list[Comment]] = {}
    for item in items:
        by_parent.setdefault(item.parent_comment_id, []).append(item)
    return by_parent.get(None, [])


@router.get("/tasks/{task_id}/comments", response_model=List[CommentRead])
async def list_comments(
    task_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> List[CommentRead]:
    task_result = await session.execute(select(Task).where(Task.id == task_id))
    task = task_result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    project = await _user_can_access_project(session, task.project_id, current_user)
    if not project:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    result = await session.execute(
        select(Comment)
        .options(*_comment_options())
        .where(Comment.task_id == task_id)
        .order_by(Comment.created_at.asc())
    )
    all_comments = list(result.scalars().unique().all())
    return [CommentRead.model_validate(c) for c in all_comments]


@router.post(
    "/tasks/{task_id}/comments", response_model=CommentRead, status_code=status.HTTP_201_CREATED
)
async def create_comment(
    task_id: UUID,
    payload: CommentCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> CommentRead:
    task_result = await session.execute(select(Task).where(Task.id == task_id))
    task = task_result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    project = await _user_can_access_project(session, task.project_id, current_user)
    if not project:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    comment = Comment(
        task_id=task_id,
        author_id=current_user.id,
        content=payload.content,
        parent_comment_id=payload.parent_comment_id,
    )
    session.add(comment)
    await session.flush()
    await record_activity(
        session,
        entity_type="comment",
        entity_id=comment.id,
        action="created",
        user_id=current_user.id,
        new_values={"task_id": str(task_id)},
    )
    await session.commit()
    result = await session.execute(
        select(Comment).options(*_comment_options()).where(Comment.id == comment.id)
    )
    fresh = result.scalar_one()
    return CommentRead.model_validate(fresh)


@router.patch("/comments/{comment_id}", response_model=CommentRead)
async def update_comment(
    comment_id: UUID,
    payload: CommentUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> CommentRead:
    result = await session.execute(
        select(Comment).options(*_comment_options()).where(Comment.id == comment_id)
    )
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if comment.author_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    comment.content = payload.content
    comment.is_edited = True
    await session.commit()
    await session.refresh(comment)
    return CommentRead.model_validate(comment)


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> None:
    result = await session.execute(select(Comment).where(Comment.id == comment_id))
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if comment.author_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    await session.delete(comment)
    await session.commit()
