from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from project_qwe.models.todo import TodoPriority, TodoStatus


class TodoBase(BaseModel):
    """Base schema for Todo items defining common attributes."""

    title: str = Field(..., min_length=1, description="Title of the todo item")
    description: str | None = Field(
        default=None,
        max_length=1000,
        description="Optional detailed description for the todo item",
    )
    status: TodoStatus = Field(
        default=TodoStatus.CREATED,
        description="Status of the todo item (created, inprogress, completed)",
    )
    priority: TodoPriority = Field(
        default=TodoPriority.MEDIUM,
        description="Priority level of the todo item (urgent, high, medium, low)",
    )
    due_at: datetime | None = Field(
        default=None,
        description="Optional due date/time for the todo item",
    )


class TodoCreate(TodoBase):
    """Payload for creating a Todo; inherits title, description, status, priority, and due_at."""

    pass


class TodoUpdate(BaseModel):
    """Payload for updating an existing Todo item. All fields are optional."""

    title: str | None = Field(
        default=None,
        min_length=1,
        description="Updated title of the todo item",
    )
    description: str | None = Field(
        default=None,
        max_length=1000,
        description="Updated description for the todo item",
    )
    status: TodoStatus | None = Field(
        default=None,
        description="Updated status of the todo item",
    )
    priority: TodoPriority | None = Field(
        default=None,
        description="Updated priority level of the todo item (urgent, high, medium, low). When None, the existing priority is preserved unchanged",
    )
    due_at: datetime | None = Field(
        default=None,
        description="Updated due date/time for the todo item",
    )


class TodoResponse(BaseModel):
    """Response model representing a complete Todo item."""

    id: int
    title: str
    description: str | None = Field(
        default=None,
        description="Detailed description of the todo item",
    )
    status: TodoStatus
    priority: TodoPriority = Field(
        ...,
        description="Priority level of the todo item (urgent, high, medium, low)",
    )
    due_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TodoPaginationResponse(BaseModel):
    items: list[TodoResponse]
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Number of items per page")
    has_next_page: bool = Field(..., description="Whether there is a subsequent page")

    model_config = ConfigDict(from_attributes=True)

