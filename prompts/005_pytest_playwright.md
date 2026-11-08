# Task: Build Authentication Demo API with Playwright Tests

## Objective

Create a fresh, standalone API module in the existing FastAPI project to demonstrate and learn three authentication mechanisms:

1. Bearer Token Authentication
2. API Key Authentication
3. Basic Authentication

This is a learning exercise for understanding how authentication works on the API side and how to test it using Playwright's APIRequestContext.

Do not use the existing Todo API for this exercise.

## Step 1: Review Existing Project

Before implementation:

- Inspect the existing FastAPI project structure.
- Review how routes, schemas, dependencies, and configuration are organized.
- Review the existing pytest and Playwright setup.
- Reuse existing project conventions and fixtures where appropriate.

Provide a short implementation plan before coding.

## Step 2: Create Authentication Demo API

Create a separate API module following the existing architecture.

Suggested structure (adapt to existing conventions):

```text
src/project_qwe/
    api/
        routes/
            auth_demo.py
    schemas/
        auth_demo.py
    services/
        auth_demo.py

tests/
    playwright/
        test_authentication.py
```

Keep the implementation lightweight. Avoid unnecessary database models or migrations. Use configured test credentials for this demonstration.

### A. Bearer Token Authentication

Endpoint:

`GET /auth-demo/bearer/profile`

Requirements:

- Accept `Authorization: Bearer <token>`.
- Validate the token.
- Return a user profile for valid credentials.
- Return HTTP 401 for missing or invalid credentials.

Use FastAPI `HTTPBearer`.

### B. API Key Authentication

Endpoint:

`GET /auth-demo/api-key/profile`

Requirements:

- Accept API key through `X-API-Key` header.
- Validate the API key.
- Return a user profile for valid credentials.
- Return HTTP 401 for missing or invalid credentials.

Use FastAPI `APIKeyHeader`.

### C. Basic Authentication

Endpoint:

`GET /auth-demo/basic/profile`

Requirements:

- Accept HTTP Basic Authentication.
- Validate username and password.
- Return a user profile for valid credentials.
- Return HTTP 401 for missing or invalid credentials.

Use FastAPI `HTTPBasic`.

## Step 3: Configuration and Security

- Store demo credentials in environment-based configuration.
- Use test-only credentials for automated tests.
- Never hardcode production secrets.
- Do not expose credentials in API responses.
- Use constant-time comparison for secret validation.
- Keep the implementation simple and educational.
- Do not introduce JWT infrastructure unless already available and necessary.

## Step 4: Playwright API Tests

Create:

`tests/playwright/test_authentication.py`

Use the existing `api_context` fixture if appropriate.

### Bearer Token Tests

- Valid token returns HTTP 200.
- Missing token returns HTTP 401.
- Invalid token returns HTTP 401.
- Validate the response body.

### API Key Tests

- Valid API key returns HTTP 200.
- Missing API key returns HTTP 401.
- Invalid API key returns HTTP 401.
- Validate the response body.

### Basic Authentication Tests

- Valid username/password returns HTTP 200.
- Missing credentials returns HTTP 401.
- Invalid username returns HTTP 401.
- Invalid password returns HTTP 401.
- Validate the response body.

## Step 5: Demonstrate Playwright Concepts

The tests should demonstrate:

1. APIRequestContext.
2. Request-level authentication.
3. Authorization headers.
4. Custom headers.
5. Bearer token authentication.
6. API key authentication.
7. Basic authentication using `http_credentials` or an appropriate Playwright request configuration.
8. Positive and negative authentication tests.
9. Response status validation.
10. Response body validation.
11. Assertions.

Where useful, demonstrate both:

- Passing credentials directly in individual requests.
- Configuring credentials when creating APIRequestContext.

Avoid excessive helper abstractions so each authentication mechanism is easy to understand.

## Step 6: Test Isolation

- Do not depend on the Todo API.
- Do not require database setup.
- Keep authentication demo tests independently runnable.
- Do not depend on test execution order.
- Use the existing test configuration and fixtures where possible.

## Step 7: Run and Review

Run:

```bash
uv run pytest tests/playwright/test_authentication.py -v
```

Also run relevant existing tests to ensure no regressions.

Do not modify Todo API behavior.

## Final Summary

Explain:

1. New files created or modified.
2. Authentication flow for each mechanism.
3. API endpoints and expected status codes.
4. How Playwright sends each type of credentials.
5. Commands to run the tests.
6. Any limitations or assumptions.

## Important Constraints

- Do not use Todo endpoints, models, or schemas.
- Do not modify `tests/playwright/test_todos.py`.
- Do not create a separate Python project.
- Do not add unnecessary database dependencies.
- Keep the example beginner-friendly.
- Follow existing FastAPI architecture and naming conventions.
- Inspect before implementing; never assume existing project structure.
