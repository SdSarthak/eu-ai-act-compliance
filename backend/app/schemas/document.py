from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime
from app.models.document import DocumentType, DocumentStatus

# ``documents.title`` is a VARCHAR(255); anything longer is a DataError on
# PostgreSQL (a 500) rather than a validation failure, so bound it here.
TITLE_MAX_LENGTH = 255


class DocumentCreate(BaseModel):
    # Strip first so a whitespace-only title fails min_length instead of
    # producing an untitled document.
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=TITLE_MAX_LENGTH)
    document_type: DocumentType
    ai_system_id: Optional[int] = Field(default=None, ge=1)
    content: Optional[str] = None


class DocumentUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: Optional[str] = Field(default=None, min_length=1, max_length=TITLE_MAX_LENGTH)
    content: Optional[str] = None
    status: Optional[DocumentStatus] = None


class DocumentResponse(BaseModel):
    id: int
    title: str
    document_type: DocumentType
    status: DocumentStatus
    content: Optional[str]
    file_path: Optional[str]
    version: str
    ai_system_id: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentGenerateRequest(BaseModel):
    """Request to generate a compliance document."""
    document_type: DocumentType
    ai_system_id: int = Field(ge=1)
    include_recommendations: bool = True
