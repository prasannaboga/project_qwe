"""Playwright API testing suite for FastAPI Todo API.

This module demonstrates end-to-end API testing using Playwright's APIRequestContext,
covering all key concepts:
1. Context lifecycle (creation, configuration, disposal without browser binaries)
2. HTTP methods (GET, POST, PUT, DELETE, and unsupported method handling)
3. Request configuration (base_url, timeouts, extra_http_headers)
4. Custom headers and response header validation
5. Query parameter handling (pagination, filtering, sorting, and 422 validation)
6. Path parameters and 404 Not Found handling
7. Request body schemas and validation errors
8. Response validation (status codes, JSON structure, content type)
9. Playwright-specific API response assertions and inspection methods
10. Complete CRUD lifecycle
11. Dynamic API chaining across sequential requests
12. Test isolation and cleanup using unique identifiers
"""

from collections.abc import Generator
import os
import socket
import threading
import time
import uuid

from playwright.sync_api import APIRequestContext, Playwright
import pytest


# ---------------------------------------------------------------------------
# Fixtures and Setup
# ---------------------------------------------------------------------------

def _is_server_ready(url: str) -> bool:
    """Check if the API server at `url` is ready and returning 200 on /health."""
    import urllib.request

    try:
        with urllib.request.urlopen(f"{url}/health", timeout=1.0) as resp:
            return resp.status == 200
    except Exception:
        return False


@pytest.fixture(scope="session")
def base_url() -> str:
    """Resolve the base URL for Playwright API testing.

    Order of precedence:
    1. Environment variable API_BASE_URL (if provided and reachable).
    2. Default development server at http://127.0.0.1:8000 (if running).
    3. An in-process background uvicorn server started on a free local port
       so tests run reliably in CI or headless test environments.
    """
    env_url = os.getenv("API_BASE_URL")
    if env_url and _is_server_ready(env_url):
        return env_url

    default_url = "http://127.0.0.1:8000"
    if _is_server_ready(default_url):
        return default_url

    # Fall back to starting an in-process uvicorn server on a random free port
    import uvicorn
    from project_qwe.main import app

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        free_port = s.getsockname()[1]

    server_url = f"http://127.0.0.1:{free_port}"
    config = uvicorn.Config(app=app, host="127.0.0.1", port=free_port, log_level="error")
    server = uvicorn.Server(config=config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    for _ in range(50):
        if _is_server_ready(server_url):
            return server_url
        time.sleep(0.1)

    return server_url


@pytest.fixture
def api_context(
    playwright: Playwright, base_url: str
) -> Generator[APIRequestContext, None, None]:
    """Provide a managed Playwright APIRequestContext fixture with automatic disposal.

    Using pytest fixtures ensures context is cleanly created and disposed even if
    test assertions fail.
    """
    context: APIRequestContext = playwright.request.new_context(
        base_url=base_url,
        extra_http_headers={"Accept": "application/json"},
    )
    try:
        yield context
    finally:
        context.dispose()


# ---------------------------------------------------------------------------
# Topic 1 & 2: APIRequestContext Lifecycle & Request Configuration
# ---------------------------------------------------------------------------

def test_api_request_context_explicit_lifecycle(
    playwright: Playwright, base_url: str
) -> None:
    """Topic 1 & 2: Demonstrate explicit creation and disposal of APIRequestContext.

    Playwright's `playwright.request.new_context()` allows sending HTTP requests
    directly without launching or installing browser binaries (Chromium, Firefox, WebKit).
    Always dispose of the context in a `finally` block or context manager to free
    underlying networking connections.
    """
    # Create request context with explicit configuration
    api_context: APIRequestContext = playwright.request.new_context(
        base_url=base_url,
        timeout=10_000,  # 10 seconds timeout for requests
    )

    try:
        # Relative URLs automatically resolve against base_url
        response = api_context.get("/health")

        assert response.status == 200
        assert response.json() == {"status": "ok"}
    finally:
        # Crucial: Dispose the context to release connection pool and resources
        api_context.dispose()


def test_request_configuration_options(playwright: Playwright, base_url: str) -> None:
    """Topic 4: Demonstrate request configuration options (base_url, timeout, extra_headers)."""
    custom_context = playwright.request.new_context(
        base_url=base_url,
        timeout=5_000,
        extra_http_headers={
            "X-Client-Name": "Playwright-Test-Suite",
            "Accept": "application/json",
        },
    )

    try:
        response = custom_context.get("/")
        assert response.status == 200
        assert response.json() == {"message": "Hello from Project QWE"}
    finally:
        custom_context.dispose()


# ---------------------------------------------------------------------------
# Topic 5: Request Headers & Response Header Validation
# ---------------------------------------------------------------------------

def test_custom_headers_and_response_headers(api_context: APIRequestContext) -> None:
    """Topic 5: Demonstrate sending request headers and validating response headers."""
    # Send custom per-request headers
    response = api_context.get(
        "/health",
        headers={"X-Custom-Trace-Id": "trace-playwright-12345"},
    )

    assert response.status == 200

    # Validate response headers dict
    headers = response.headers
    assert "content-type" in headers
    assert "application/json" in headers["content-type"]

    # Validate response headers array format
    headers_array = response.headers_array
    content_type_header = next(
        (h for h in headers_array if h["name"].lower() == "content-type"), None
    )
    assert content_type_header is not None
    assert "application/json" in content_type_header["value"]


# ---------------------------------------------------------------------------
# Topic 3, 8 & 9: HTTP Methods, Request Body & Response Validation
# ---------------------------------------------------------------------------

def test_http_method_post_create(api_context: APIRequestContext) -> None:
    """Topic 3, 8 & 9: Demonstrate POST request with JSON body and response schema validation."""
    unique_title = f"Playwright POST Test - {uuid.uuid4().hex[:8]}"
    payload = {
        "title": unique_title,
        "description": "Created via Playwright APIRequestContext",
        "priority": "high",
        "status": "created",
    }

    response = api_context.post("/todos", data=payload)

    # Status validation: 201 Created
    assert response.status == 201
    assert response.ok is True

    # Response JSON validation
    data = response.json()
    assert isinstance(data["id"], int)
    assert data["title"] == unique_title
    assert data["description"] == payload["description"]
    assert data["priority"] == "high"
    assert data["status"] == "created"
    assert "created_at" in data
    assert "updated_at" in data

    # Clean up created resource
    delete_response = api_context.delete(f"/todos/{data['id']}")
    assert delete_response.status == 200


def test_http_method_get_list_and_by_id(api_context: APIRequestContext) -> None:
    """Topic 3 & 7: Demonstrate GET collection and GET single item by path parameter."""
    # First create a todo to ensure at least one known item exists
    unique_title = f"Playwright GET Test - {uuid.uuid4().hex[:8]}"
    create_res = api_context.post(
        "/todos",
        data={"title": unique_title, "priority": "medium"},
    )
    assert create_res.status == 201
    created_id = create_res.json()["id"]

    try:
        # GET collection
        list_res = api_context.get("/todos")
        assert list_res.status == 200
        list_data = list_res.json()
        assert "items" in list_data
        assert "page" in list_data
        assert "per_page" in list_data
        assert "has_next_page" in list_data

        # GET single item using path parameter
        item_res = api_context.get(f"/todos/{created_id}")
        assert item_res.status == 200
        item_data = item_res.json()
        assert item_data["id"] == created_id
        assert item_data["title"] == unique_title
    finally:
        api_context.delete(f"/todos/{created_id}")


def test_http_method_put_update(api_context: APIRequestContext) -> None:
    """Topic 3 & 8: Demonstrate PUT request with partial update payload."""
    # Create initial todo
    initial_title = f"Playwright PUT Initial - {uuid.uuid4().hex[:8]}"
    create_res = api_context.post(
        "/todos",
        data={"title": initial_title, "priority": "low"},
    )
    assert create_res.status == 201
    todo_id = create_res.json()["id"]

    try:
        # Update using PUT /todos/{id}
        updated_title = f"Playwright PUT Updated - {uuid.uuid4().hex[:8]}"
        update_res = api_context.put(
            f"/todos/{todo_id}",
            data={
                "title": updated_title,
                "status": "inprogress",
                "priority": "urgent",
            },
        )
        assert update_res.status == 200
        updated_data = update_res.json()
        assert updated_data["id"] == todo_id
        assert updated_data["title"] == updated_title
        assert updated_data["status"] == "inprogress"
        assert updated_data["priority"] == "urgent"
    finally:
        api_context.delete(f"/todos/{todo_id}")


def test_http_method_delete(api_context: APIRequestContext) -> None:
    """Topic 3 & 11: Demonstrate DELETE request and verify deletion."""
    create_res = api_context.post(
        "/todos",
        data={"title": f"Playwright DELETE Test - {uuid.uuid4().hex[:8]}"},
    )
    assert create_res.status == 201
    todo_id = create_res.json()["id"]

    # Delete the created todo
    delete_res = api_context.delete(f"/todos/{todo_id}")
    assert delete_res.status == 200
    assert delete_res.json() == {"message": "Todo deleted successfully"}

    # Verify that requesting the deleted todo returns 404 Not Found
    get_res = api_context.get(f"/todos/{todo_id}")
    assert get_res.status == 404
    assert get_res.json()["detail"] == f"Todo with id {todo_id} not found"


def test_http_method_patch_not_supported_by_api(api_context: APIRequestContext) -> None:
    """Topic 3 (Unsupported Method): Demonstrate that PATCH returns 405 Method Not Allowed.

    Note on Todo API design:
    The FastAPI Todo API routes define `PUT /todos/{id}` for updating todo items.
    There is no `PATCH` route registered in `src/project_qwe/api/todos.py`.
    FastAPI automatically returns `405 Method Not Allowed` for unregistered methods.
    """
    create_res = api_context.post(
        "/todos",
        data={"title": f"Playwright PATCH Test - {uuid.uuid4().hex[:8]}"},
    )
    assert create_res.status == 201
    todo_id = create_res.json()["id"]

    try:
        # Attempt PATCH on /todos/{id}
        patch_res = api_context.patch(
            f"/todos/{todo_id}",
            data={"title": "Patched Title"},
        )
        # FastAPI returns 405 Method Not Allowed
        assert patch_res.status == 405
    finally:
        api_context.delete(f"/todos/{todo_id}")


# ---------------------------------------------------------------------------
# Topic 6: Query Parameters (Filtering, Sorting, Pagination, Validation)
# ---------------------------------------------------------------------------

def test_query_parameters_pagination_and_sorting(api_context: APIRequestContext) -> None:
    """Topic 6: Demonstrate query parameters for pagination, sorting, and priority filtering."""
    # Seed two items with specific priorities
    tag = uuid.uuid4().hex[:6]
    res1 = api_context.post(
        "/todos",
        data={"title": f"Item 1 - {tag}", "priority": "urgent"},
    )
    res2 = api_context.post(
        "/todos",
        data={"title": f"Item 2 - {tag}", "priority": "low"},
    )
    id1 = res1.json()["id"]
    id2 = res2.json()["id"]

    try:
        # Test query parameters: page, per_page, sort, priority
        response = api_context.get(
            "/todos",
            params={
                "page": 1,
                "per_page": 10,
                "sort": "created_at:desc",
                "priority": "urgent",
            },
        )
        assert response.status == 200
        data = response.json()
        assert data["page"] == 1
        assert data["per_page"] == 10
        assert isinstance(data["items"], list)

        # Ensure all returned items match the requested priority filter
        for item in data["items"]:
            assert item["priority"] == "urgent"
    finally:
        api_context.delete(f"/todos/{id1}")
        api_context.delete(f"/todos/{id2}")


def test_query_parameters_validation_422(api_context: APIRequestContext) -> None:
    """Topic 6: Demonstrate 422 Unprocessable Entity on invalid query parameters."""
    # Invalid sort field
    res_bad_sort = api_context.get("/todos", params={"sort": "invalid_column:asc"})
    assert res_bad_sort.status == 422

    # Invalid sort direction
    res_bad_dir = api_context.get("/todos", params={"sort": "created_at:sideways"})
    assert res_bad_dir.status == 422

    # Out of bounds page (< 1)
    res_bad_page = api_context.get("/todos", params={"page": 0})
    assert res_bad_page.status == 422

    # Invalid priority enum value
    res_bad_priority = api_context.get("/todos", params={"priority": "super_urgent"})
    assert res_bad_priority.status == 422


# ---------------------------------------------------------------------------
# Topic 7: Path Parameters and 404 Not Found Handling
# ---------------------------------------------------------------------------

def test_path_parameters_not_found_handling(api_context: APIRequestContext) -> None:
    """Topic 7: Demonstrate path parameters and 404 Not Found response validation."""
    non_existent_id = 999_999_999

    # GET non-existent
    get_res = api_context.get(f"/todos/{non_existent_id}")
    assert get_res.status == 404
    assert get_res.json()["detail"] == f"Todo with id {non_existent_id} not found"

    # PUT non-existent
    put_res = api_context.put(
        f"/todos/{non_existent_id}",
        data={"title": "Non-existent Update"},
    )
    assert put_res.status == 404
    assert put_res.json()["detail"] == f"Todo with id {non_existent_id} not found"

    # DELETE non-existent
    delete_res = api_context.delete(f"/todos/{non_existent_id}")
    assert delete_res.status == 404
    assert delete_res.json()["detail"] == f"Todo with id {non_existent_id} not found"


# ---------------------------------------------------------------------------
# Topic 8: Request Body Validation (Pydantic Schema Errors)
# ---------------------------------------------------------------------------

def test_request_body_schema_validation_errors(api_context: APIRequestContext) -> None:
    """Topic 8: Test JSON request bodies validation for create and update operations."""
    # Missing required field 'title'
    missing_title_res = api_context.post(
        "/todos",
        data={"description": "Missing title"},
    )
    assert missing_title_res.status == 422
    assert "detail" in missing_title_res.json()

    # Empty title string (min_length=1 violation)
    empty_title_res = api_context.post(
        "/todos",
        data={"title": ""},
    )
    assert empty_title_res.status == 422

    # Invalid status enum
    invalid_status_res = api_context.post(
        "/todos",
        data={"title": "Valid Title", "status": "not_a_valid_status"},
    )
    assert invalid_status_res.status == 422

    # Invalid priority enum
    invalid_priority_res = api_context.post(
        "/todos",
        data={"title": "Valid Title", "priority": "highest"},
    )
    assert invalid_priority_res.status == 422


# ---------------------------------------------------------------------------
# Topic 9 & 10: Playwright API Response Methods and Assertions
# ---------------------------------------------------------------------------

def test_playwright_api_response_methods_and_assertions(
    api_context: APIRequestContext,
) -> None:
    """Topic 9 & 10: Demonstrate Playwright APIResponse methods and clear assertions.

    Playwright's APIResponse provides convenient inspection methods:
    - `response.ok`: Returns True for 200-299 status codes.
    - `response.status`: HTTP status code integer.
    - `response.status_text`: HTTP status description ("OK", "Created", etc.).
    - `response.url`: Full resolved URL including base_url.
    - `response.text()`: Raw response body as string.
    - `response.json()`: Deserialized JSON body as Python dict/list.
    - `response.headers`: Dictionary of headers.
    """
    unique_title = f"Playwright Inspection - {uuid.uuid4().hex[:8]}"
    create_res = api_context.post(
        "/todos",
        data={"title": unique_title, "priority": "medium"},
    )

    try:
        # Check response status properties
        assert create_res.ok is True
        assert create_res.status == 201
        assert create_res.status_text in ("Created", "")

        # Check response URL
        assert "/todos" in create_res.url

        # Check text body representation
        raw_text = create_res.text()
        assert isinstance(raw_text, str)
        assert unique_title in raw_text

        # Check JSON parsed body
        json_data = create_res.json()
        assert isinstance(json_data, dict)
        assert json_data["title"] == unique_title

        # Check headers
        assert "application/json" in create_res.headers.get("content-type", "")
    finally:
        todo_id = create_res.json().get("id")
        if todo_id:
            api_context.delete(f"/todos/{todo_id}")


# ---------------------------------------------------------------------------
# Topic 11: Complete CRUD Operations
# ---------------------------------------------------------------------------

def test_complete_crud_lifecycle(api_context: APIRequestContext) -> None:
    """Topic 11: Complete CRUD Operations.

    1. CREATE a Todo (POST /todos)
    2. RETRIEVE the created Todo (GET /todos/{id})
    3. UPDATE the Todo (PUT /todos/{id})
    4. DELETE the Todo (DELETE /todos/{id})
    5. VERIFY behavior after deletion (GET /todos/{id} -> 404)
    """
    title = f"CRUD LifeCycle - {uuid.uuid4().hex[:8]}"
    desc = "Lifecycle initial description"

    # 1. CREATE
    create_res = api_context.post(
        "/todos",
        data={"title": title, "description": desc, "priority": "low"},
    )
    assert create_res.status == 201
    todo = create_res.json()
    todo_id = todo["id"]

    try:
        # 2. RETRIEVE
        get_res = api_context.get(f"/todos/{todo_id}")
        assert get_res.status == 200
        fetched = get_res.json()
        assert fetched["id"] == todo_id
        assert fetched["title"] == title
        assert fetched["description"] == desc
        assert fetched["status"] == "created"
        assert fetched["priority"] == "low"

        # 3. UPDATE
        updated_title = f"{title} [EDITED]"
        updated_desc = "Lifecycle updated description"
        update_res = api_context.put(
            f"/todos/{todo_id}",
            data={
                "title": updated_title,
                "description": updated_desc,
                "status": "inprogress",
                "priority": "high",
            },
        )
        assert update_res.status == 200
        updated = update_res.json()
        assert updated["title"] == updated_title
        assert updated["description"] == updated_desc
        assert updated["status"] == "inprogress"
        assert updated["priority"] == "high"

        # 4. DELETE
        delete_res = api_context.delete(f"/todos/{todo_id}")
        assert delete_res.status == 200
        assert delete_res.json()["message"] == "Todo deleted successfully"

        # 5. VERIFY EXPECTED BEHAVIOR AFTER DELETION
        verify_res = api_context.get(f"/todos/{todo_id}")
        assert verify_res.status == 404
        assert verify_res.json()["detail"] == f"Todo with id {todo_id} not found"
    except Exception:
        # Ensure cleanup in case of test failure during intermediate assertions
        api_context.delete(f"/todos/{todo_id}")
        raise


# ---------------------------------------------------------------------------
# Topic 12: API Chaining
# ---------------------------------------------------------------------------

def test_api_chaining_workflow(api_context: APIRequestContext) -> None:
    """Topic 12: API Chaining.

    Demonstrates extracting dynamic output from one API request and passing
    it into subsequent requests across an end-to-end workflow without hardcoding IDs:
    1. POST /todos -> extract dynamic todo_id
    2. GET /todos/{todo_id} -> verify dynamic item
    3. PUT /todos/{todo_id} -> update status to completed
    4. GET /todos?priority=... -> verify chained item is included in collection
    5. DELETE /todos/{todo_id} -> delete dynamic item
    6. DELETE /todos/{todo_id} -> verify second delete returns 404 (not found)
    """
    task_name = f"Chained Task - {uuid.uuid4().hex[:8]}"

    # Step 1: Create a Todo item and extract dynamic ID
    step1_res = api_context.post(
        "/todos",
        data={"title": task_name, "priority": "urgent", "status": "created"},
    )
    assert step1_res.status == 201
    todo_id: int = step1_res.json()["id"]
    assert isinstance(todo_id, int)

    try:
        # Step 2: Use extracted ID to retrieve details
        step2_res = api_context.get(f"/todos/{todo_id}")
        assert step2_res.status == 200
        assert step2_res.json()["title"] == task_name

        # Step 3: Use extracted ID to advance status to completed
        step3_res = api_context.put(
            f"/todos/{todo_id}",
            data={"status": "completed"},
        )
        assert step3_res.status == 200
        assert step3_res.json()["status"] == "completed"

        # Step 4: Query list filtered by priority="urgent" and find our chained ID
        step4_res = api_context.get("/todos", params={"priority": "urgent"})
        assert step4_res.status == 200
        urgent_ids = [item["id"] for item in step4_res.json()["items"]]
        assert todo_id in urgent_ids

        # Step 5: Delete using the dynamic ID
        step5_res = api_context.delete(f"/todos/{todo_id}")
        assert step5_res.status == 200

        # Step 6: Verify second delete returns 404
        step6_res = api_context.delete(f"/todos/{todo_id}")
        assert step6_res.status == 404
    except Exception:
        api_context.delete(f"/todos/{todo_id}")
        raise
