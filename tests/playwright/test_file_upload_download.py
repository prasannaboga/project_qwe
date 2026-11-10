"""Playwright API testing suite for FastAPI file upload and download endpoints.

This module demonstrates:
1. APIRequestContext usage for multipart/form-data file uploads.
2. Positive and negative test cases for file upload validation:
   - Valid .txt and .jpg files.
   - File size boundaries: 0 bytes (empty), exactly 5 KiB, > 5 KiB.
   - Unsupported extensions (.jpeg, .png, .pdf).
   - Mismatched MIME types and invalid magic byte content signatures.
   - Missing required form fields.
3. File download validation:
   - Status codes (200, 404).
   - Response headers (Content-Type, Content-Disposition, Content-Length).
   - Content integrity (byte-for-byte match).
4. End-to-end upload and download API chaining.
5. Dynamic test data generation, isolation, and automatic file cleanup.
"""

from collections.abc import Generator
from pathlib import Path
import uuid

from playwright.sync_api import APIRequestContext
import pytest

from project_qwe.services import file_service

FIXTURES_DIR = Path("tests/fixtures")
SAMPLE_TXT_PATH = FIXTURES_DIR / "sample.txt"
SAMPLE_JPG_PATH = FIXTURES_DIR / "sample.jpg"


@pytest.fixture
def uploaded_files() -> Generator[list[str], None, None]:
    """Track uploaded file IDs and safely delete them after test execution."""
    file_ids: list[str] = []
    try:
        yield file_ids
    finally:
        for file_id in file_ids:
            file_service.delete_file(file_id)


# ---------------------------------------------------------------------------
# Section A: File Upload Tests
# ---------------------------------------------------------------------------


def test_upload_valid_txt_file(
    api_context: APIRequestContext, uploaded_files: list[str]
) -> None:
    """Validate successful upload of a valid .txt file."""
    assert SAMPLE_TXT_PATH.exists(), "Sample txt fixture must exist"
    file_bytes = SAMPLE_TXT_PATH.read_bytes()

    response = api_context.post(
        "/files/upload",
        multipart={
            "file": {
                "name": "sample.txt",
                "mimeType": "text/plain",
                "buffer": file_bytes,
            }
        },
    )

    assert response.status == 201
    data = response.json()
    assert "id" in data
    assert data["filename"] == "sample.txt"
    assert data["content_type"] == "text/plain"
    assert data["size"] == len(file_bytes)

    uploaded_files.append(data["id"])


def test_upload_valid_jpg_file(
    api_context: APIRequestContext, uploaded_files: list[str]
) -> None:
    """Validate successful upload of a valid .jpg file."""
    assert SAMPLE_JPG_PATH.exists(), "Sample jpg fixture must exist"
    file_bytes = SAMPLE_JPG_PATH.read_bytes()

    response = api_context.post(
        "/files/upload",
        multipart={
            "file": {
                "name": "sample.jpg",
                "mimeType": "image/jpeg",
                "buffer": file_bytes,
            }
        },
    )

    assert response.status == 201
    data = response.json()
    assert "id" in data
    assert data["filename"] == "sample.jpg"
    assert data["content_type"] == "image/jpeg"
    assert data["size"] == len(file_bytes)

    uploaded_files.append(data["id"])


@pytest.mark.parametrize(
    "filename,mime_type",
    [
        ("document.pdf", "application/pdf"),
        ("image.jpeg", "image/jpeg"),  # .jpeg is explicitly rejected per requirements
        ("graphic.png", "image/png"),
        ("script.py", "text/x-python"),
    ],
)
def test_upload_unsupported_extensions(
    api_context: APIRequestContext, filename: str, mime_type: str
) -> None:
    """Validate rejection of disallowed file extensions with HTTP 415."""
    response = api_context.post(
        "/files/upload",
        multipart={
            "file": {
                "name": filename,
                "mimeType": mime_type,
                "buffer": b"Dummy test payload",
            }
        },
    )

    assert response.status == 415
    data = response.json()
    assert "Unsupported file extension" in data["detail"]


def test_upload_file_larger_than_5kib(api_context: APIRequestContext) -> None:
    """Validate rejection of files exceeding 5 KiB (5120 bytes) with HTTP 413."""
    oversized_bytes = b"A" * 5121

    response = api_context.post(
        "/files/upload",
        multipart={
            "file": {
                "name": "oversized.txt",
                "mimeType": "text/plain",
                "buffer": oversized_bytes,
            }
        },
    )

    assert response.status == 413
    data = response.json()
    assert "exceeds maximum allowed size" in data["detail"]


def test_upload_empty_file(api_context: APIRequestContext) -> None:
    """Validate rejection of empty (0-byte) files with HTTP 400."""
    response = api_context.post(
        "/files/upload",
        multipart={
            "file": {
                "name": "empty.txt",
                "mimeType": "text/plain",
                "buffer": b"",
            }
        },
    )

    assert response.status == 400
    data = response.json()
    assert "empty" in data["detail"].lower()


def test_upload_incorrect_mime_type(api_context: APIRequestContext) -> None:
    """Validate rejection when declared MIME type does not match extension."""
    response = api_context.post(
        "/files/upload",
        multipart={
            "file": {
                "name": "notes.txt",
                "mimeType": "image/jpeg",  # Mismatch for .txt
                "buffer": b"Valid text content",
            }
        },
    )

    assert response.status == 415
    data = response.json()
    assert "does not match expected" in data["detail"]


def test_upload_mismatched_extension_and_content_jpg(
    api_context: APIRequestContext,
) -> None:
    """Validate rejection when a .jpg file does not contain valid JPEG magic bytes."""
    fake_jpg_content = b"This is plain text disguised as a JPG file!"

    response = api_context.post(
        "/files/upload",
        multipart={
            "file": {
                "name": "fake.jpg",
                "mimeType": "image/jpeg",
                "buffer": fake_jpg_content,
            }
        },
    )

    assert response.status == 415
    data = response.json()
    assert "JPEG image signature" in data["detail"]


def test_upload_mismatched_extension_and_content_txt(
    api_context: APIRequestContext,
) -> None:
    """Validate rejection when a .txt file contains invalid UTF-8 bytes."""
    # 0xFF 0xFE is an invalid start for standard UTF-8 text
    invalid_utf8_content = b"\xff\xfe\x00\x00\x12\x34"

    response = api_context.post(
        "/files/upload",
        multipart={
            "file": {
                "name": "invalid.txt",
                "mimeType": "text/plain",
                "buffer": invalid_utf8_content,
            }
        },
    )

    assert response.status == 415
    data = response.json()
    assert "UTF-8" in data["detail"]


def test_upload_exactly_5kib(
    api_context: APIRequestContext, uploaded_files: list[str]
) -> None:
    """Validate successful upload of a file that is exactly 5 KiB (5120 bytes)."""
    exact_5kib_bytes = b"B" * 5120

    response = api_context.post(
        "/files/upload",
        multipart={
            "file": {
                "name": "exact_5kib.txt",
                "mimeType": "text/plain",
                "buffer": exact_5kib_bytes,
            }
        },
    )

    assert response.status == 201
    data = response.json()
    assert data["size"] == 5120
    uploaded_files.append(data["id"])


def test_upload_without_file_field(api_context: APIRequestContext) -> None:
    """Validate HTTP 422 when multipart upload omits the required 'file' field."""
    response = api_context.post(
        "/files/upload",
        multipart={
            "wrong_field_name": {
                "name": "sample.txt",
                "mimeType": "text/plain",
                "buffer": b"Some content",
            }
        },
    )

    assert response.status == 422


# ---------------------------------------------------------------------------
# Section B: File Download Tests
# ---------------------------------------------------------------------------


def test_download_existing_file(
    api_context: APIRequestContext, uploaded_files: list[str]
) -> None:
    """Validate successful download of an existing file."""
    # First upload a file
    file_bytes = b"Download test content: " + uuid.uuid4().hex.encode("utf-8")
    upload_res = api_context.post(
        "/files/upload",
        multipart={
            "file": {
                "name": "test_download.txt",
                "mimeType": "text/plain",
                "buffer": file_bytes,
            }
        },
    )
    assert upload_res.status == 201
    file_id = upload_res.json()["id"]
    uploaded_files.append(file_id)

    # Download the file
    download_res = api_context.get(
        f"/files/{file_id}/download",
        headers={"Accept": "*/*"},
    )
    assert download_res.status == 200
    assert download_res.body() == file_bytes


def test_download_non_existing_file(api_context: APIRequestContext) -> None:
    """Validate HTTP 404 when downloading an unknown file ID."""
    fake_id = "0" * 32
    response = api_context.get(f"/files/{fake_id}/download")
    assert response.status == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


def test_download_invalid_file_id(api_context: APIRequestContext) -> None:
    """Validate HTTP 404 and traversal protection for invalid file IDs."""
    response = api_context.get("/files/../../etc/passwd/download")
    assert response.status == 404


def test_download_response_headers_and_content_disposition(
    api_context: APIRequestContext, uploaded_files: list[str]
) -> None:
    """Validate headers: Content-Type, Content-Length, and Content-Disposition."""
    filename = "report_test.txt"
    content = b"Financial report line 1\nLine 2"
    upload_res = api_context.post(
        "/files/upload",
        multipart={
            "file": {
                "name": filename,
                "mimeType": "text/plain",
                "buffer": content,
            }
        },
    )
    assert upload_res.status == 201
    file_id = upload_res.json()["id"]
    uploaded_files.append(file_id)

    download_res = api_context.get(
        f"/files/{file_id}/download",
        headers={"Accept": "*/*"},
    )
    assert download_res.status == 200

    headers = download_res.headers
    # Content-Type should match text/plain (FastAPI may include charset=utf-8)
    assert "text/plain" in headers["content-type"]
    assert headers["content-length"] == str(len(content))
    # Content-Disposition must preserve original filename
    assert "content-disposition" in headers
    assert f'filename="{filename}"' in headers["content-disposition"]


def test_download_binary_content_integrity(
    api_context: APIRequestContext, uploaded_files: list[str]
) -> None:
    """Validate byte-for-byte binary integrity when downloading a JPEG image."""
    assert SAMPLE_JPG_PATH.exists()
    original_bytes = SAMPLE_JPG_PATH.read_bytes()

    upload_res = api_context.post(
        "/files/upload",
        multipart={
            "file": {
                "name": "photo.jpg",
                "mimeType": "image/jpeg",
                "buffer": original_bytes,
            }
        },
    )
    assert upload_res.status == 201
    file_id = upload_res.json()["id"]
    uploaded_files.append(file_id)

    download_res = api_context.get(
        f"/files/{file_id}/download",
        headers={"Accept": "*/*"},
    )
    assert download_res.status == 200
    downloaded_bytes = download_res.body()
    assert downloaded_bytes == original_bytes
    assert len(downloaded_bytes) == len(original_bytes)


# ---------------------------------------------------------------------------
# Section C: API Chaining Workflow
# ---------------------------------------------------------------------------


def test_upload_download_chaining_workflow(
    api_context: APIRequestContext, uploaded_files: list[str]
) -> None:
    """Demonstrate end-to-end API chaining:
    1. Prepare dynamic unique test payload.
    2. Upload file via Playwright POST /files/upload.
    3. Extract generated file ID from JSON response.
    4. Fetch file via Playwright GET /files/{file_id}/download.
    5. Verify exact byte match, status codes, and filename preservation.
    """
    unique_suffix = uuid.uuid4().hex
    original_filename = f"chained_test_{unique_suffix}.txt"
    original_content = f"Playwright API Chaining Test Content: {unique_suffix}\n".encode(
        "utf-8"
    )

    # 1. Upload
    upload_res = api_context.post(
        "/files/upload",
        multipart={
            "file": {
                "name": original_filename,
                "mimeType": "text/plain",
                "buffer": original_content,
            }
        },
    )
    assert upload_res.status == 201
    upload_payload = upload_res.json()
    extracted_file_id = upload_payload["id"]
    assert extracted_file_id
    uploaded_files.append(extracted_file_id)

    # 2. Download using chained ID
    download_res = api_context.get(
        f"/files/{extracted_file_id}/download",
        headers={"Accept": "*/*"},
    )
    assert download_res.status == 200
    assert download_res.body() == original_content

    # 3. Header verification
    assert f'filename="{original_filename}"' in download_res.headers.get(
        "content-disposition", ""
    )
