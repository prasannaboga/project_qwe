from datetime import datetime, timezone
import enum

from sqlalchemy import DateTime, Enum, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from project_qwe.config.database import Base


class TodoStatus(str, enum.Enum):
    CREATED = "created"
    INPROGRESS = "inprogress"
    COMPLETED = "completed"


class Todo(Base):
    __tablename__ = "todos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
        default=None,
    )
    status: Mapped[TodoStatus] = mapped_column(
        Enum(
            TodoStatus,
            values_callable=lambda x: [e.value for e in x],
            native_enum=False,
            create_constraint=True,
            name="todostatus",
        ),
        default=TodoStatus.CREATED,
        nullable=False,
        index=True,
    )
    due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
