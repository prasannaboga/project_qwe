"""Service layer handling file storage, validation, and retrieval."""

import json
from pathlib import Path
import re
import uuid
from typing import Any

from fastapi import HTTPException, UploadFile, status

MAX_FILE_SIZE_BYTES = 5 * 1024  # 5 KiB = 5120 bytes
UPLOAD_DIR = Path("data/uploads")

ALLOWED_EXTENSIONS = {".txt", ".jpg"}
ALLOWED_MIME_TYPES = {
    ".txt": "text/plain",
    ".jpg": "image/jpeg",
}
JPEG_MAGIC_BYTES = b"\xff\xd8\xff"
SAFE_ID_PATTERN = re.compile(r"^[0-9a-fA-F]{32}$")


def ensure_upload_dir() -> Path:
    """Ensure the uploads directory exists and return its path."""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    return UPLOAD_DIR


async def validate_and_save_file(file: UploadFile) -> dict[str, Any]:
    """Validate an uploaded file and persist it safely to the upload directory.

    Validations performed:
    1. Check filename presence and extension (only .txt and .jpg allowed; reject .jpeg etc.).
    2. Check content-type header matches allowed MIME type for the extension.
    3. Read file content safely, ensuring:
       - File is not empty (len == 0).
       - File size does not exceed MAX_FILE_SIZE_BYTES (5 KiB).
    4. Validate binary content signatures:
       - .jpg: must start with standard JPEG SOI marker (0xFF 0xD8 0xFF).
       - .txt: must be decodable as valid UTF-8 text.

    Returns:
        dict containing id, filename, content_type, size.

    Raises:
        HTTPException: with appropriate status code (400, 413, 415, 422).
    """
    original_filename = file.filename or ""
    if not original_filename.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Missing or empty filename.",
        )

    file_ext = Path(original_filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file extension '{file_ext}'. Only .txt and .jpg are allowed.",
        )

    expected_mime = ALLOWED_MIME_TYPES[file_ext]
    if file.content_type != expected_mime:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Content-Type '{file.content_type}' does not match expected "
                f"'{expected_mime}' for extension '{file_ext}'."
            ),
        )

    # Read content up to MAX_FILE_SIZE_BYTES + 1 to detect oversized files safely
    content = await file.read(MAX_FILE_SIZE_BYTES + 1)

    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is empty. Uploaded file must contain at least 1 byte.",
        )

    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {MAX_FILE_SIZE_BYTES} bytes (5 KiB).",
        )

    # Validate actual content signatures
    if file_ext == ".jpg":
        if not content.startswith(JPEG_MAGIC_BYTES):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="File content does not match valid JPEG image signature.",
            )
    elif file_ext == ".txt":
        try:
            content.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="File content is not valid UTF-8 text.",
            )

    # Persist file using a generated UUID, keeping the original extension
    upload_dir = ensure_upload_dir()
    file_id = uuid.uuid4().hex
    actual_path = upload_dir / f"{file_id}{file_ext}"
    meta_path = upload_dir / f"{file_id}.json"

    metadata = {
        "id": file_id,
        "filename": Path(original_filename).name,  # Sanitize to basename
        "content_type": expected_mime,
        "size": len(content),
        "ext": file_ext,
    }

    try:
        actual_path.write_bytes(content)
        meta_path.write_text(json.dumps(metadata), encoding="utf-8")
    except Exception as exc:
        # Clean up partial writes if an unexpected error occurs
        if actual_path.exists():
            actual_path.unlink()
        if meta_path.exists():
            meta_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store uploaded file.",
        ) from exc

    return metadata


def get_file_for_download(file_id: str) -> tuple[Path, str, str]:
    """Locate an uploaded file by ID and return its actual file path, original filename, and media type.

    Validates file_id to prevent directory traversal and verifies both the file and metadata exist.
    The file is stored with its original extension (e.g. .txt, .jpg) rather than as .bin.

    Returns:
        tuple of (file_path, original_filename, content_type)

    Raises:
        HTTPException(404): if file is not found or file_id format is invalid.
    """
    if not SAFE_ID_PATTERN.match(file_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File with id '{file_id}' not found.",
        )

    upload_dir = ensure_upload_dir()
    meta_path = upload_dir / f"{file_id}.json"

    # Prevent path traversal on metadata
    try:
        meta_path.resolve().relative_to(upload_dir.resolve())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File with id '{file_id}' not found.",
        )

    if not meta_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File with id '{file_id}' not found.",
        )

    try:
        metadata = json.loads(meta_path.read_text(encoding="utf-8"))
        filename = metadata.get("filename", file_id)
        content_type = metadata.get("content_type", "application/octet-stream")
        ext = metadata.get("ext", Path(filename).suffix.lower())
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File metadata for id '{file_id}' is invalid or missing.",
        )

    actual_path = upload_dir / f"{file_id}{ext}"

    # Prevent path traversal on the actual file path
    try:
        actual_path.resolve().relative_to(upload_dir.resolve())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File with id '{file_id}' not found.",
        )

    if not actual_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File with id '{file_id}' not found.",
        )

    return actual_path, filename, content_type


def delete_file(file_id: str) -> bool:
    """Delete a file and its metadata if they exist. Useful for test cleanup.

    Reads the stored extension from metadata to find the actual file path.
    """
    if not SAFE_ID_PATTERN.match(file_id):
        return False
    upload_dir = ensure_upload_dir()
    meta_path = upload_dir / f"{file_id}.json"

    deleted = False

    # Determine the actual file extension from stored metadata, if available
    ext: str | None = None
    if meta_path.is_file():
        try:
            metadata = json.loads(meta_path.read_text(encoding="utf-8"))
            ext = metadata.get("ext")
            if ext is None:
                stored_filename = metadata.get("filename", "")
                if stored_filename:
                    ext = Path(stored_filename).suffix.lower()
        except Exception:
            pass

    if ext:
        actual_path = upload_dir / f"{file_id}{ext}"
        if actual_path.exists():
            actual_path.unlink()
            deleted = True
    else:
        # Fallback: attempt to remove any known-extension file for this id
        for fallback_ext in ALLOWED_EXTENSIONS:
            candidate = upload_dir / f"{file_id}{fallback_ext}"
            if candidate.exists():
                candidate.unlink()
                deleted = True

    if meta_path.exists():
        meta_path.unlink()
        deleted = True

    return deleted
