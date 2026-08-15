from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from project_qwe.models.todo import TodoStatus


class TodoBase(BaseModel):
    title: str = Field(..., min_length=1, description="Title of the todo item")
    status: TodoStatus = Field(
        default=TodoStatus.CREATED,
        description="Status of the todo item (created, inprogress, completed)",
    )
    due_at: datetime | None = Field(
        default=None,
        description="Optional due date/time for the todo item",
    )


class TodoCreate(TodoBase):
    pass


class TodoUpdate(BaseModel):
    title: str | None = Field(
        default=None,
        min_length=1,
        description="Updated title of the todo item",
    )
    status: TodoStatus | None = Field(
        default=None,
        description="Updated status of the todo item",
    )
    due_at: datetime | None = Field(
        default=None,
        description="Updated due date/time for the todo item",
    )


class TodoResponse(BaseModel):
    id: int
    title: str
    status: TodoStatus
    due_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
