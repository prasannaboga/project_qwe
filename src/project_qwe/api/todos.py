from fastapi import APIRouter

router = APIRouter(prefix="/todos", tags=["todos"])


@router.get("")
@router.get("/")
def get_todos() -> dict[str, str]:
    """Placeholder endpoint for listing all todos."""
    return {"message": "Get todos is not implemented yet"}


@router.get("/{todo_id}")
def get_todo(todo_id: int) -> dict[str, str]:
    """Placeholder endpoint for retrieving a single todo by ID."""
    return {"message": f"Get todo {todo_id} is not implemented yet"}


@router.post("")
@router.post("/")
def create_todo() -> dict[str, str]:
    """Placeholder endpoint for creating a new todo."""
    return {"message": "Todo creation is not implemented yet"}


@router.put("/{todo_id}")
def update_todo(todo_id: int) -> dict[str, str]:
    """Placeholder endpoint for updating an existing todo."""
    return {"message": f"Update todo {todo_id} is not implemented yet"}


@router.delete("/{todo_id}")
def delete_todo(todo_id: int) -> dict[str, str]:
    """Placeholder endpoint for deleting a todo."""
    return {"message": f"Delete todo {todo_id} is not implemented yet"}
