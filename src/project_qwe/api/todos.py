from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from project_qwe.config.database import get_db
from project_qwe.schemas.todo import TodoCreate, TodoResponse, TodoUpdate
from project_qwe.services import todo_service

router = APIRouter(prefix="/todos", tags=["todos"])


@router.get("", response_model=list[TodoResponse])
@router.get("/", response_model=list[TodoResponse], include_in_schema=False)
def get_todos(db: Session = Depends(get_db)) -> list[TodoResponse]:
    """Retrieve all todos."""
    todos = todo_service.get_todos(db)
    return [TodoResponse.model_validate(todo) for todo in todos]


@router.get("/{todo_id}", response_model=TodoResponse)
def get_todo(todo_id: int, db: Session = Depends(get_db)) -> TodoResponse:
    """Retrieve a specific todo by ID."""
    todo = todo_service.get_todo_by_id(db, todo_id)
    if todo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Todo with id {todo_id} not found",
        )
    return TodoResponse.model_validate(todo)


@router.post("", response_model=TodoResponse, status_code=status.HTTP_201_CREATED)
@router.post(
    "/",
    response_model=TodoResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
def create_todo(
    todo_data: TodoCreate, db: Session = Depends(get_db)
) -> TodoResponse:
    """Create a new todo."""
    todo = todo_service.create_todo(db, todo_data)
    return TodoResponse.model_validate(todo)


@router.put("/{todo_id}", response_model=TodoResponse)
def update_todo(
    todo_id: int, todo_data: TodoUpdate, db: Session = Depends(get_db)
) -> TodoResponse:
    """Update an existing todo."""
    todo = todo_service.update_todo(db, todo_id, todo_data)
    if todo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Todo with id {todo_id} not found",
        )
    return TodoResponse.model_validate(todo)


@router.delete("/{todo_id}")
def delete_todo(todo_id: int, db: Session = Depends(get_db)) -> dict[str, str]:
    """Delete a todo by ID."""
    deleted = todo_service.delete_todo(db, todo_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Todo with id {todo_id} not found",
        )
    return {"message": "Todo deleted successfully"}
