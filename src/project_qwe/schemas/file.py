"""Pydantic schemas for file upload and download operations."""

from pydantic import BaseModel, ConfigDict


class FileUploadResponse(BaseModel):
    """Metadata response returned after a successful file upload."""

    id: str
    filename: str
    content_type: str
    size: int

    model_config = ConfigDict(extra="forbid")
