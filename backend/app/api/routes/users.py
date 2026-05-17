from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session, require_roles
from app.core.security import hash_password, verify_password
from app.models.user import User, UserRole
from app.schemas.user import PasswordChange, UserPublic, UserUpdate, UserAdminUpdate


router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserPublic)
async def get_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.patch("/me", response_model=UserPublic)
async def update_me(
    payload: UserUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> User:
    if payload.username and payload.username != current_user.username:
        result = await session.execute(select(User).where(User.username == payload.username))
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Username already taken"
            )
        current_user.username = payload.username
    if payload.full_name is not None:
        current_user.full_name = payload.full_name
    if payload.avatar_url is not None:
        current_user.avatar_url = payload.avatar_url
    await session.commit()
    await session.refresh(current_user)
    return current_user


@router.post("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    payload: PasswordChange,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> None:
    if not verify_password(payload.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Old password is incorrect"
        )
    current_user.hashed_password = hash_password(payload.new_password)
    await session.commit()


@router.get("", response_model=List[UserPublic])
async def list_users(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> List[User]:
    if current_user.role in (UserRole.superadmin, UserRole.admin):
        # Admins can see all users (including inactive ones) to manage them
        result = await session.execute(
            select(User).order_by(User.username)
        )
    else:
        # Regular users only see active users
        result = await session.execute(
            select(User).where(User.is_active.is_(True)).order_by(User.username)
        )
    return list(result.scalars().all())


@router.patch("/{user_id}/admin", response_model=UserPublic)
async def admin_update_user(
    user_id: UUID,
    payload: UserAdminUpdate,
    session: AsyncSession = Depends(get_session),
    admin_user: User = Depends(require_roles(UserRole.superadmin, UserRole.admin)),
) -> User:
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.role == UserRole.superadmin and admin_user.role != UserRole.superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmins can modify superadmin users",
        )

    if payload.role is not None:
        user.role = payload.role
    if payload.is_active is not None:
        if user.id == admin_user.id and payload.is_active is False:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot deactivate your own account",
            )
        user.is_active = payload.is_active

    await session.commit()
    await session.refresh(user)
    return user
