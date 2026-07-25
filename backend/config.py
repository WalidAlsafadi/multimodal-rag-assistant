"""Central configuration for InsightLens."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

APPLICATION_NAME = "InsightLens"
APPLICATION_SUBTITLE = "Multimodal RAG for Intelligent Document Exploration"

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
UPLOAD_DIR = PROJECT_ROOT / "uploads"
VECTORSTORE_DIR = PROJECT_ROOT / "vectorstore"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
VECTORSTORE_DIR.mkdir(parents=True, exist_ok=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_IMAGE_DETAIL = os.getenv("OPENAI_IMAGE_DETAIL", "low")

BACKEND_HOST = os.getenv("BACKEND_HOST", "0.0.0.0")
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8000"))
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
FRONTEND_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "FRONTEND_ORIGINS",
        ",".join(
            {
                FRONTEND_ORIGIN,
                "http://127.0.0.1:5173",
                "http://localhost:5174",
                "http://127.0.0.1:5174",
                "http://localhost:5199",
                "http://127.0.0.1:5199",
            }
        ),
    ).split(",")
    if origin.strip()
]

_bundled_poppler_paths = sorted(BASE_DIR.glob("poppler-*/Library/bin"))
DEFAULT_POPPLER_PATH = str(_bundled_poppler_paths[-1]) if _bundled_poppler_paths else None
POPPLER_PATH = os.getenv("POPPLER_PATH") or DEFAULT_POPPLER_PATH
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "20"))
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
MAX_VISUAL_PDF_PAGES = int(os.getenv("MAX_VISUAL_PDF_PAGES", "20"))
MAX_FILENAME_CHARS = int(os.getenv("MAX_FILENAME_CHARS", "120"))
MAX_ACTIVE_DOCUMENTS = int(os.getenv("MAX_ACTIVE_DOCUMENTS", "25"))

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))
TOP_K_RESULTS = int(os.getenv("TOP_K_RESULTS", "5"))

VISUAL_DESCRIPTION_MAX_TOKENS = int(os.getenv("VISUAL_DESCRIPTION_MAX_TOKENS", "900"))
ANSWER_MAX_TOKENS = int(os.getenv("ANSWER_MAX_TOKENS", "700"))
MAX_CONTEXT_CHARS = int(os.getenv("MAX_CONTEXT_CHARS", "8000"))
QUESTION_MAX_CHARS = int(os.getenv("QUESTION_MAX_CHARS", "1000"))

SUPPORTED_EXTENSIONS = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".bmp": "image",
    ".tif": "image",
    ".tiff": "image",
}

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}


def require_openai_api_key() -> str:
    """Return the OpenAI API key or raise a short configuration error."""
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is required for visual analysis and answering.")
    return OPENAI_API_KEY
