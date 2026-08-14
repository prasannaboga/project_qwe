from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TodoBase(BaseModel):
    title: str = Field(..., min_length=1, description="Title of the todo item")


class TodoCreate(TodoBase):
    pass


class TodoUpdate(BaseModel):
    title: str = Field(..., min_length=1, description="Updated title of the todo item")


class TodoResponse(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
