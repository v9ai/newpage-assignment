import shutil
from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_session
from app.models import Document

router = APIRouter(prefix="/api/documents", tags=["documents"])

ALLOWED_TYPES = {
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".md": "text/markdown",
}


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    status: str
    size_bytes: int
    mime: str
    error: str | None
    created_at: datetime


def stored_path(doc: Document) -> Path:
    ext = Path(doc.filename).suffix.lower()
    return Path(get_settings().upload_dir) / f"{doc.id}{ext}"


@router.post("", status_code=201, response_model=DocumentOut)
def upload_document(
    file: UploadFile, session: Annotated[Session, Depends(get_session)]
) -> Document:
    settings = get_settings()
    filename = file.filename or ""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{ext or 'unknown'}'. Allowed: pdf, txt, md.",
        )
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if file.size is not None and file.size > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File is larger than the {settings.max_upload_mb} MB limit.",
        )

    doc = Document(
        filename=filename,
        status="uploaded",
        size_bytes=file.size or 0,
        mime=ALLOWED_TYPES[ext],
    )
    session.add(doc)
    session.commit()
    session.refresh(doc)

    dest = stored_path(doc)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("wb") as out:
        shutil.copyfileobj(file.file, out)

    return doc


@router.get("", response_model=list[DocumentOut])
def list_documents(session: Annotated[Session, Depends(get_session)]) -> list[Document]:
    return list(session.scalars(select(Document).order_by(Document.created_at.desc())))


@router.delete("/{doc_id}", status_code=204)
def delete_document(doc_id: int, session: Annotated[Session, Depends(get_session)]) -> None:
    doc = session.get(Document, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    stored_path(doc).unlink(missing_ok=True)
    session.delete(doc)
    session.commit()
