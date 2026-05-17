import enum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class UserRole(str, enum.Enum):
    superadmin = "superadmin"
    admin = "admin"
    manager = "manager"
    member = "member"


if TYPE_CHECKING:
    from app.models.comment import Comment
    from app.models.project import Project, ProjectMember
    from app.models.task import Task


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"), default=UserRole.member, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    owned_projects: Mapped[List["Project"]] = relationship(
        back_populates="owner", foreign_keys="Project.owner_id"
    )
    project_memberships: Mapped[List["ProjectMember"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    assigned_tasks: Mapped[List["Task"]] = relationship(
        back_populates="assignee", foreign_keys="Task.assignee_id"
    )
    reported_tasks: Mapped[List["Task"]] = relationship(
        back_populates="reporter", foreign_keys="Task.reporter_id"
    )
    comments: Mapped[List["Comment"]] = relationship(back_populates="author")
