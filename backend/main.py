"""FastAPI API for InsightLens."""
from __future__ import annotations

import asyncio
import re
import uuid
from pathlib import Path
from typing import Any
from zipfile import BadZipFile, ZipFile

from fastapi import FastAPI, File, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field

from .config import (
    APPLICATION_NAME,
    FRONTEND_ORIGINS,
    MAX_ACTIVE_DOCUMENTS,
    MAX_FILENAME_CHARS,
    MAX_UPLOAD_BYTES,
    MAX_UPLOAD_MB,
    OPENAI_MODEL,
    QUESTION_MAX_CHARS,
    SECURITY_HEADERS,
    SUPPORTED_EXTENSIONS,
    UPLOAD_DIR,
)
from .utils.document_processor import DocumentProcessingError, DocumentProcessor
from .utils.rag_engine import AnswerGenerationError, RAGEngine

app = FastAPI(
    title=f"{APPLICATION_NAME} API",
    description="Multimodal RAG API for document exploration.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
)

doc_processor = DocumentProcessor()
rag_engine = RAGEngine()
rag_engine.clear_index()
documents: dict[str, dict[str, Any]] = {}
session_lock = asyncio.Lock()
SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._ -]+")


class HealthResponse(BaseModel):
    status: str
    application: str
    model: str
    documents: int


class QuestionRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=QUESTION_MAX_CHARS)


class Source(BaseModel):
    document_id: str
    filename: str
    page: int | None = None
    content_type: str
    snippet: str
    score: float | None = None


class AnswerResponse(BaseModel):
    answer: str
    sources: list[Source]


class DocumentSummary(BaseModel):
    id: str
    filename: str
    file_type: str
    pages: int | None = None
    text_items: int
    visual_items: int
    warnings: list[str] = Field(default_factory=list)


class UploadResponse(BaseModel):
    document: DocumentSummary
    warnings: list[str]


class DocumentsResponse(BaseModel):
    documents: list[DocumentSummary]


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response: Response = await call_next(request)
    for name, value in SECURITY_HEADERS.items():
        response.headers.setdefault(name, value)
    return response


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        application=APPLICATION_NAME,
        model=OPENAI_MODEL,
        documents=len(documents),
    )


@app.post("/upload", response_model=UploadResponse)
async def upload_file(request: Request, file: UploadFile = File(...)) -> UploadResponse:
    _reject_oversized_content_length(request)
    safe_filename = _safe_display_filename(file.filename)
    if not safe_filename:
        raise HTTPException(status_code=400, detail="Filename cannot be empty.")

    ext = Path(safe_filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        )

    document_id = str(uuid.uuid4())
    saved_path = UPLOAD_DIR / f"{document_id}{ext}"

    try:
        async with session_lock:
            if len(documents) >= MAX_ACTIVE_DOCUMENTS:
                raise HTTPException(
                    status_code=429,
                    detail=f"Document limit reached. Clear or delete documents before uploading more.",
                )

        size = 0
        with saved_path.open("wb") as handle:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail=f"File exceeds the {MAX_UPLOAD_MB} MB upload limit.")
                handle.write(chunk)

        _validate_saved_file(saved_path, ext)
        result = doc_processor.process_file(saved_path, document_id, safe_filename)
        summary = result["document"]
        summary["warnings"] = result["warnings"]
        async with session_lock:
            documents[document_id] = {
                "summary": summary,
                "items": result["items"],
                "file_path": saved_path,
            }
            _rebuild_index()
        return UploadResponse(document=DocumentSummary(**summary), warnings=result["warnings"])
    except HTTPException:
        _cleanup_file(saved_path)
        raise
    except DocumentProcessingError as exc:
        _cleanup_file(saved_path)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        _cleanup_file(saved_path)
        raise HTTPException(status_code=500, detail="The file could not be processed.") from exc
    finally:
        await file.close()


@app.get("/documents", response_model=DocumentsResponse)
async def list_documents() -> DocumentsResponse:
    async with session_lock:
        summaries = [DocumentSummary(**entry["summary"]) for entry in documents.values()]
    return DocumentsResponse(documents=summaries)


@app.post("/ask", response_model=AnswerResponse)
async def ask_question(request: QuestionRequest) -> AnswerResponse:
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    async with session_lock:
        has_documents = bool(documents)
    if not has_documents:
        raise HTTPException(status_code=400, detail="Upload and index at least one document before asking questions.")

    try:
        result = rag_engine.query(question)
    except AnswerGenerationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="The question could not be answered.") from exc
    return AnswerResponse(answer=result["answer"], sources=[Source(**source) for source in result["sources"]])


@app.delete("/documents/{document_id}")
async def delete_document(document_id: str) -> dict[str, str]:
    async with session_lock:
        entry = documents.pop(document_id, None)
        if entry is not None:
            _cleanup_file(entry["file_path"])
            _rebuild_index()
    if entry is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    return {"message": "Document deleted successfully."}


@app.delete("/documents")
async def clear_documents() -> dict[str, str]:
    async with session_lock:
        for entry in list(documents.values()):
            _cleanup_file(entry["file_path"])
        documents.clear()
        rag_engine.clear_index()
    return {"message": "All documents cleared successfully."}


def _rebuild_index() -> None:
    items = [item for entry in documents.values() for item in entry["items"]]
    rag_engine.rebuild_index(items)


def _cleanup_file(path: Path) -> None:
    try:
        resolved = path.resolve()
        if not resolved.is_relative_to(UPLOAD_DIR.resolve()):
            return
        if resolved.exists() and resolved.is_file():
            resolved.unlink()
    except (OSError, ValueError):
        pass


def _safe_display_filename(filename: str | None) -> str:
    raw_name = Path(filename or "").name.strip()
    if not raw_name:
        return ""
    cleaned = SAFE_FILENAME_RE.sub("_", raw_name)
    cleaned = cleaned.strip(" ._")
    if len(cleaned) > MAX_FILENAME_CHARS:
        stem = Path(cleaned).stem[: MAX_FILENAME_CHARS - len(Path(cleaned).suffix) - 1]
        cleaned = f"{stem}{Path(cleaned).suffix}"
    return cleaned


def _reject_oversized_content_length(request: Request) -> None:
    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit() and int(content_length) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"File exceeds the {MAX_UPLOAD_MB} MB upload limit.")


def _validate_saved_file(path: Path, ext: str) -> None:
    if ext == ".pdf":
        with path.open("rb") as handle:
            if handle.read(5) != b"%PDF-":
                raise HTTPException(status_code=400, detail="Uploaded file content does not match its extension.")
        return

    if ext == ".docx":
        try:
            with ZipFile(path) as archive:
                names = set(archive.namelist())
                if "[Content_Types].xml" not in names or "word/document.xml" not in names:
                    raise HTTPException(status_code=400, detail="Uploaded file content does not match its extension.")
        except BadZipFile as exc:
            raise HTTPException(status_code=400, detail="Uploaded file content does not match its extension.") from exc
        return

    if ext in {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}:
        try:
            with Image.open(path) as image:
                image.verify()
        except (UnidentifiedImageError, OSError) as exc:
            raise HTTPException(status_code=400, detail="Uploaded file content does not match its extension.") from exc
        return
