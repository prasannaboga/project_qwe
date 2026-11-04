# Task: Complete Playwright API Testing for Todo API

## Context

I have an existing Python project with a FastAPI Todo API.

The project already has:

- Basic project setup
- Pytest configured
- Playwright installed
- Existing application code, database setup, and tests

I am learning Playwright API testing. I want to extend the existing project rather than create a new project.

**Primary target file:** `tests/playwright/test_todos.py`

## Step 1: Review the Existing Project

Before making changes:

1. Inspect the project structure and `pyproject.toml`.
2. Review the FastAPI Todo API routes, request/response schemas, and service layer.
3. Review existing pytest fixtures and database setup.
4. Review `tests/playwright/` and the current `test_todos.py`.
5. Identify the available Todo endpoints(src/project_qwe/api/todos.py) and their actual HTTP methods, request fields, response formats, and status codes.

Do not assume endpoint paths, fields, or response structures. Derive them from the existing code.

Provide a short summary of the current setup and implementation plan before coding.

## Step 2: Implement the Learning Topics

Implement the following topics in `tests/playwright/test_todos.py`:

1. **Test Project Setup**
   - Follow the existing pytest and Playwright configuration.
   - Use the existing fixtures where appropriate.
   - Do not introduce a new test framework or duplicate project setup.

2. **APIRequestContext**
   - Use Playwright's `APIRequestContext`; do not install browser binaries for API-only tests.
   - Configure the API base URL using the project's existing configuration where possible.
   - Correctly create and dispose of the request context.

3. **HTTP Methods**
   - GET
   - POST
   - PUT
   - PATCH
   - DELETE
   - Cover only methods supported by the existing API.

4. **Request Configuration**
   - Demonstrate relevant request options such as `base_url`, timeout, and request context configuration.
   - Avoid unnecessary configuration that does not benefit the tests.

5. **Headers**
   - Demonstrate sending request headers.
   - Validate response headers where useful.

6. **Query Parameters**
   - Test supported query parameters.
   - Use the actual parameters implemented by the API.

7. **Path Parameters**
   - Test endpoints that use Todo IDs or other path parameters.
   - Include a not-found case where supported.

8. **Request Body**
   - Test JSON request bodies for create and update operations.
   - Use the actual request schemas.

9. **Response Validation**
   - Validate response status, JSON structure, and important field values.
   - Validate response content type where appropriate.

10. **Assertions**
    - Use clear pytest assertions.
    - Use Playwright API response methods appropriately.
    - Keep assertions readable and specific.

11. **CRUD Operations**
    - Create a Todo.
    - Retrieve the created Todo.
    - Update it using supported PUT/PATCH operations.
    - Delete it.
    - Verify the expected behavior after deletion.

12. **API Chaining**
    - Use a response from one API request in a subsequent request.
    - Example: create a Todo, extract its ID, retrieve it, update it, and delete it.
    - Avoid hardcoded IDs.
    - Keep chained operations understandable and easy to debug.

## Step 3: Test Isolation and Reliability

- Use unique test data to avoid conflicts.
- Use the existing database fixtures and test database configuration.
- Do not depend on test execution order.
- Each test should be independently runnable unless it is explicitly testing API chaining.
- Clean up created data when necessary.
- Do not use production data or a production database.
- Do not change application behavior merely to make a test pass.

## Step 4: Learning-Friendly Code

I am learning Playwright API testing, so:

- Keep the code simple and readable.
- Prefer explicit code over clever abstractions.
- Add short comments explaining the Playwright concepts being demonstrated.
- Avoid unnecessary helper classes, custom frameworks, or excessive fixtures.
- Keep examples in `tests/playwright/test_todos.py`.
- Reuse existing project conventions.

## Step 5: Run and Review

After implementation:

1. Run the new Playwright API tests.
2. Run relevant existing tests to ensure no regressions.
3. Fix failures caused by the implementation.
4. Do not hide failures with skipped tests or weakened assertions.
5. Summarize:
   - Files changed
   - Topics covered
   - Tests executed and their results
   - Any topics not implemented because the API does not support them

## Important Constraints

- Do not create a separate project.
- Do not replace the existing pytest setup.
- Do not invent API endpoints or response fields.
- Do not add unsupported API features just to satisfy the syllabus.
- Keep the main implementation in `tests/playwright/test_todos.py`.
- If a required topic cannot be demonstrated with the current Todo API, explain why and suggest the smallest appropriate next step.
