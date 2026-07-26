#!/usr/bin/env python3
"""Start the InsightLens FastAPI backend."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import uvicorn
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backend"))


def check_dependencies() -> bool:
    required = [
        "fastapi",
        "uvicorn",
        "openai",
        "PyPDF2",
        "docx",
        "pdf2image",
        "PIL",
        "chromadb",
        "llama_index.core",
        "sentence_transformers",
    ]
    missing: list[str] = []
    for package in required:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)

    if missing:
        print("Missing backend dependencies:")
        for package in missing:
            print(f"  - {package}")
        print("\nInstall them with: python -m pip install -r requirements.txt")
        return False
    return True


def check_openai_key() -> bool:
    load_dotenv(ROOT / ".env")
    if not os.getenv("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is required for image analysis and grounded answers.")
        print("Add it to .env before starting the backend.")
        return False
    return True


def main() -> None:
    print("InsightLens backend")
    print("-------------------")
    if not check_dependencies() or not check_openai_key():
        sys.exit(1)

    from backend.config import BACKEND_HOST, BACKEND_PORT

    print(f"API: http://{BACKEND_HOST}:{BACKEND_PORT}")
    print(f"Docs: http://{BACKEND_HOST}:{BACKEND_PORT}/docs")
    uvicorn.run(
        "backend.main:app",
        host=BACKEND_HOST,
        port=BACKEND_PORT,
        reload=True,
        app_dir=str(ROOT),
    )


if __name__ == "__main__":
    main()
