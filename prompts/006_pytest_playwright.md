## 1. Objective

Build a new, independent FastAPI API module to demonstrate:

- File Upload using FastAPI.
- File Download using FastAPI.
- File validation and error handling.
- Playwright Python API testing.
- Upload and Download API chaining.

This is a hands-on learning exercise. I want to understand and implement the code myself with AI assistance.

**Existing project:** `project_qwe`

**New Playwright test file:**
`tests/playwright/test_file_upload_download.py`

**Important:** Do not modify any existing application code, APIs, tests, fixtures, or configurations unless a new dependency or configuration is genuinely required. Do not touch existing Todo or authentication examples.

---

## 2. Functional Requirements

### Supported file types

Allow only:

| File type  | Extension | Maximum size |
| ---------- | --------- | -----------: |
| Text file  | `.txt`    |         5 KB |
| JPEG image | `.jpg`    |         5 KB |

Use 5 KiB (5 × 1024 bytes) as the maximum file size.

Reject `.jpeg`, `.png`, `.pdf`, and all other extensions.

### Upload API

Create a new endpoint:

`POST /files/upload`

Expected behavior:

1. Accept a file using multipart/form-data.
2. Validate the file extension.
3. Validate the content type.
4. Validate the actual file content, not just the filename or MIME type.
5. Validate the file size.
6. Generate a unique server-side file identifier.
7. Store the uploaded file safely.
8. Return file metadata and an identifier.

Example response shape (adapt as appropriate):

```json
{
  "id": "unique-file-id",
  "filename": "sample.txt",
  "content_type": "text/plain",
  "size": 1024
}
```

Do not expose the physical server storage path.

### Download API

Create a new endpoint:

`GET /files/{file_id}/download`

Expected behavior:

1. Accept a file identifier.
2. Locate the uploaded file.
3. Return the file as a downloadable response.
4. Preserve the original filename in Content-Disposition.
5. Return an appropriate error when the file does not exist.

Use FastAPI's appropriate file response mechanism.

---

## 3. Validation and Error Handling

Cover the following cases.

### Upload validation

- Valid `.txt` file.
- Valid `.jpg` file.
- Unsupported extension.
- `.jpeg` extension.
- Incorrect MIME type.
- Extension and actual content mismatch.
- Empty file.
- File larger than 5 KiB.
- File exactly 5 KiB.
- Missing file field.
- Invalid or malformed upload request.

### Download validation

- Download an existing file.
- Download a non-existing file ID.
- Invalid file ID.
- Verify downloaded content matches uploaded content.
- Verify filename and Content-Disposition headers.

Use appropriate HTTP status codes and consistent error response formats.

Suggested status codes:

| Scenario                        | Expected status |
| ------------------------------- | --------------: |
| Successful upload               |             201 |
| Successful download             |             200 |
| Unsupported file type           |      415 or 400 |
| File too large                  |             413 |
| Missing or invalid request data |             422 |
| File not found                  |             404 |

Choose a consistent validation strategy and document the decisions.

---

## 4. Implementation Architecture

First inspect the existing project and follow its conventions.

Create a separate module for file operations.

Possible structure:

```text
app/
    api/
        routes/
            file_upload.py
    services/
        file_storage.py
    schemas/
        file_upload.py

tests/
    playwright/
        test_file_upload_download.py
```

The structure is illustrative. Adapt it to the actual repository.

### Storage requirements

- Use a dedicated upload directory.
- Do not store files inside the source-code directory.
- Use generated identifiers instead of trusting user-supplied filenames.
- Prevent path traversal.
- Avoid overwriting existing files.
- Keep storage operations separate from route handling.
- Provide a simple cleanup strategy for test files.
- Do not introduce a database unless the existing architecture requires one.

### Security considerations

- Never trust the filename or Content-Type supplied by the client.
- Validate actual content signatures.
- For JPEG, verify JPEG signature markers.
- For text files, validate UTF-8 text content if appropriate.
- Handle malformed and empty files safely.
- Avoid returning internal filesystem paths or exception details.
- Ensure downloaded files can only be accessed through valid generated identifiers.

---

## 5. Playwright API Testing

Create:

`tests/playwright/test_file_upload_download.py`

Use the existing pytest and Playwright configuration.

Reuse existing fixtures where appropriate. Do not modify existing fixture implementations.

### A. File Upload Tests

Demonstrate:

1. Upload `.txt`.
2. Upload `.jpg`.
3. Upload unsupported extension.
4. Upload file larger than 5 KiB.
5. Upload empty file.
6. Upload with incorrect MIME type.
7. Upload with mismatched extension and content.
8. Upload exactly 5 KiB.
9. Upload without the required file field.

### B. File Download Tests

Demonstrate:

1. Download an existing file.
2. Download a non-existing file.
3. Validate response status.
4. Validate response headers.
5. Validate Content-Disposition.
6. Validate downloaded file contents.
7. Validate downloaded filename.

### C. API Chaining

Implement one complete workflow:

1. Prepare a test file.
2. Upload the file using Playwright.
3. Extract the returned file ID.
4. Use the file ID in the download endpoint.
5. Download the file.
6. Compare downloaded bytes with original bytes.
7. Validate filename and metadata.

Avoid hardcoded file IDs.

### D. Playwright Concepts

Demonstrate:

- APIRequestContext.
- Multipart file upload.
- File name and MIME type.
- Request configuration.
- Response validation.
- Response headers.
- Response body.
- Binary response handling.
- Positive and negative assertions.
- API chaining.

Use Playwright's API request multipart support rather than browser UI automation.

Keep the examples readable and avoid excessive helper abstractions.

---

## 6. Test Data and Isolation

- Generate test files dynamically.
- Do not commit unnecessary sample files.
- Use unique filenames.
- Keep test data small.
- Clean up uploaded files after tests.
- Ensure tests can run independently.
- Do not depend on test execution order.
- Do not use production storage.

For JPEG tests, use a small valid JPEG fixture or generate suitable test bytes. Do not rely only on a fake filename.

---

## 7. Learning and Implementation Workflow

**This is the most important requirement.**

I do not want Codex to implement the entire feature automatically.

Work as a senior developer mentoring me.

Follow this workflow:

### Phase 1: Project review

- Inspect existing project structure.
- Identify the correct place for new endpoints.
- Identify existing dependencies and fixtures.
- Explain the proposed implementation.
- Do not change any files yet.

### Phase 2: Design

Explain:

- How FastAPI receives uploaded files.
- What `UploadFile` does.
- How multipart/form-data works.
- How file size and content validation should work.
- How FastAPI returns downloadable files.
- How Playwright sends multipart requests.

Do not dump the complete implementation.

### Phase 3: Guided implementation

Work in small steps.

For each step:

1. Explain what we are implementing.
2. Explain why it is needed.
3. Identify the file to modify.
4. Give me the task or a small code example.
5. Let me implement it.
6. Review my implementation.
7. Point out mistakes and suggest improvements.
8. Move to the next step only after I confirm.

Suggested order:

- Step 1: Create the file upload route.
- Step 2: Implement extension and MIME validation.
- Step 3: Implement file size validation.
- Step 4: Implement safe file storage.
- Step 5: Implement download endpoint.
- Step 6: Add error handling.
- Step 7: Write Playwright upload tests.
- Step 8: Write Playwright download tests.
- Step 9: Implement upload/download API chaining.
- Step 10: Run the complete test suite.

### Phase 4: Code review

Review my code for:

- Python best practices.
- FastAPI conventions.
- Correct HTTP status codes.
- Security issues.
- File handling and resource cleanup.
- Test isolation.
- Playwright best practices.
- Readability and maintainability.

Prefer simple code that I can understand over sophisticated abstractions.

---

## 8. Strict AI Coding Rules

- Do not generate all files at once.
- Do not make large code changes without my approval.
- Do not silently modify existing files.
- Do not rewrite existing tests.
- Do not introduce unnecessary dependencies.
- Do not create an overengineered file-storage framework.
- Do not implement features before explaining them.
- Do not move to the next phase automatically.
- Do not assume an endpoint or configuration exists without inspecting the project.
- Do not fix unrelated issues.

If a change to an existing file is unavoidable, explain why and show the proposed change before applying it.

**My goal is to write and understand most of the code myself. AI should guide, review, and help debug—not replace my implementation.**

---

## 9. Final Acceptance Criteria

The exercise is complete when:

- A new FastAPI upload endpoint works.
- A new FastAPI download endpoint works.
- Only `.txt` and `.jpg` files are accepted.
- The maximum upload size is 5 KiB.
- Invalid uploads are rejected safely.
- Downloaded content matches uploaded content.
- Missing files return the expected error.
- Playwright tests cover positive and negative scenarios.
- Upload/download chaining works.
- Existing application functionality and tests remain unchanged.

Start with **Phase 1: Project review**. Do not write code until I approve the implementation plan.

project_qwe/
├── data/
│ └── uploads/ # Uploaded files stored by FastAPI
│
├── tests/
│ ├── fixtures/ # Test files (.txt and .jpg)
│ │ ├── sample.txt
│ │ └── sample.jpg
│ │
│ └── playwright/
│ └── test_file_upload_download.py

## Directory and File Storage Conventions

Follow these exact project directories:

### 1. Test Fixtures

Location:

`tests/fixtures/`

- Store sample `.txt` and `.jpg` files here.
- Use these files as input for Playwright upload tests.
- Include valid test files for both supported formats.
- Include or generate test data for boundary cases (empty file, exactly 5 KiB, and greater than 5 KiB).
- Do not store uploaded files in this directory.

### 2. Uploaded Files

Location:

`data/uploads/`

- FastAPI must store uploaded files in this directory.
- Create the directory automatically if it does not exist.
- Use generated unique file identifiers for stored filenames.
- Prevent path traversal and filename collisions.
- Do not expose physical storage paths in API responses.
- Ensure download operations resolve files only within this directory.
- Keep test uploads isolated and clean them up after tests.

### 3. Important Constraints

- Do not create alternative fixture or upload directories.
- Do not modify existing files under `tests/fixtures/`.
- Do not commit runtime-uploaded files.
- Add `data/uploads/` to `.gitignore` if it is not already ignored.
- Preserve existing project conventions.
- Explain any required changes before applying them.
