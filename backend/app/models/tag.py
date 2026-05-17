from typing import TYPE_CHECKING, List

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin


if TYPE_CHECKING:
    from app.models.task import Task


class Tag(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "tags"

    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    color: Mapped[str] = mapped_column(String(16), default="#888888", nullable=False)

    tasks: Mapped[List["Task"]] = relationship(secondary="task_tags", back_populates="tags")
