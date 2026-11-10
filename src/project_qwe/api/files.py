"""API routes for file upload and download operations."""

from fastapi import APIRouter, File, UploadFile, status
from fastapi.responses import FileResponse

from project_qwe.schemas.file import FileUploadResponse
from project_qwe.services import file_service

router = APIRouter(prefix="/files", tags=["files"])


@router.post(
    "/upload",
    response_model=FileUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a file",
    description="Upload a .txt or .jpg file up to 5 KiB in size.",
)
async def upload_file(file: UploadFile = File(...)) -> FileUploadResponse:
    """Accept multipart file upload, validate contents, and persist safely."""
    try:
        metadata = await file_service.validate_and_save_file(file)
        return FileUploadResponse(**metadata)
    finally:
        await file.close()


@router.get(
    "/{file_id}/download",
    response_class=FileResponse,
    summary="Download a file",
    description="Download a previously uploaded file by its unique identifier.",
)
def download_file(file_id: str) -> FileResponse:
    """Download a file with original filename preserved in Content-Disposition."""
    path, filename, content_type = file_service.get_file_for_download(file_id)
    return FileResponse(
        path=path,
        media_type=content_type,
        filename=filename,
    )
