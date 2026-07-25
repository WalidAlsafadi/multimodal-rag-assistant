"""
FastAPI Backend for RAG Project.
Provides endpoints for file upload, document processing, and question answering.
"""
import os
import shutil
from typing import List, Optional
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import UPLOAD_DIR, SUPPORTED_EXTENSIONS, GROQ_API_KEY, LLAMA_CLOUD_API_KEY
from utils.document_processor import DocumentProcessor
from utils.rag_engine import RAGEngine



POPPLER_PATH = os.path.join(os.path.dirname(__file__), "poppler-26.02.0", "Library", "bin")
os.environ["PATH"] += os.pathsep + POPPLER_PATH

# Initialize FastAPI app
app = FastAPI(
    title="RAG API",
    description="Retrieval-Augmented Generation API for document Q&A with image analysis",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
doc_processor = DocumentProcessor()
rag_engine = RAGEngine()

# Track processed documents
processed_documents = []


# Pydantic models
class QuestionRequest(BaseModel):
    question: str
    analyze_images: bool = True


class AnswerResponse(BaseModel):
    answer: str
    sources: List[dict]
    image_analysis: Optional[List[dict]] = None


class StatusResponse(BaseModel):
    status: str
    documents_count: int
    api_keys_configured: dict


@app.get("/", response_model=StatusResponse)
async def root():
    """Get API status and configuration."""
    return StatusResponse(
        status="RAG API is running",
        documents_count=len(processed_documents),
        api_keys_configured={
            "groq": bool(GROQ_API_KEY),
            "llama_cloud": bool(LLAMA_CLOUD_API_KEY),
        },
    )


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a document file (PDF, Word, or Image).
    Processes the file and indexes it for RAG.
    """
    # Validate file extension
    ext = Path(file.filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format. Supported: {list(SUPPORTED_EXTENSIONS.keys())}"
        )

    # Save uploaded file
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")
    finally:
        file.file.close()

    # Process the document
    try:
        result = doc_processor.process_file(file_path)

        # Analyze images if present
        if result["images"] and GROQ_API_KEY:
            result["images"] = doc_processor.analyze_images(result["images"])

            # Append image descriptions to text
            image_descriptions = []
            for img in result["images"]:
                if img.get("description"):
                    image_descriptions.append(
                        f"[Image from {Path(file.filename).name}]: {img['description']}"
                    )
            if image_descriptions:
                result["text"] += "\n\n=== IMAGE ANALYSIS ===\n" + "\n\n".join(image_descriptions)

        # Add to processed documents
        doc_entry = {
            "filename": file.filename,
            "text": result["text"],
            "images": result["images"],
            "metadata": result["metadata"],
        }
        processed_documents.append(doc_entry)

        # Re-index all documents
        index_success = rag_engine.index_documents(processed_documents)

        return {
            "message": f"File '{file.filename}' uploaded and processed successfully",
            "document_info": {
                "filename": file.filename,
                "text_length": len(result["text"]),
                "images_found": len(result["images"]),
                "metadata": result["metadata"],
            },
            "indexed": index_success,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")


@app.post("/ask", response_model=AnswerResponse)
async def ask_question(request: QuestionRequest):
    """
    Ask a question about the uploaded documents.
    Uses RAG to retrieve relevant context and generate an answer.
    """
    if not processed_documents:
        raise HTTPException(
            status_code=400,
            detail="No documents uploaded yet. Please upload a document first."
        )

    # Get RAG answer
    rag_result = rag_engine.query(request.question)

    # Collect image analysis if requested
    image_analysis = None
    if request.analyze_images:
        image_analysis = []
        for doc in processed_documents:
            for img in doc.get("images", []):
                if img.get("description"):
                    image_analysis.append({
                        "document": doc["filename"],
                        "description": img["description"],
                    })

    return AnswerResponse(
        answer=rag_result["answer"],
        sources=rag_result["sources"],
        image_analysis=image_analysis,
    )


@app.get("/documents")
async def list_documents():
    """List all uploaded and processed documents."""
    return {
        "documents": [
            {
                "filename": doc["filename"],
                "text_length": len(doc["text"]),
                "images_count": len(doc.get("images", [])),
                "metadata": doc["metadata"],
            }
            for doc in processed_documents
        ]
    }


@app.delete("/documents")
async def clear_documents():
    """Clear all uploaded documents and the vector index."""
    global processed_documents
    processed_documents = []

    # Clear vector store
    rag_engine.clear_index()

    # Clear upload directory (keep directory, remove files)
    for item in os.listdir(UPLOAD_DIR):
        item_path = os.path.join(UPLOAD_DIR, item)
        try:
            if os.path.isfile(item_path):
                os.remove(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
        except Exception as e:
            print(f"Error removing {item_path}: {e}")

    return {"message": "All documents cleared successfully"}


@app.delete("/documents/{filename}")
async def delete_document(filename: str):
    """Delete a specific document."""
    global processed_documents

    # Remove from processed documents
    processed_documents = [d for d in processed_documents if d["filename"] != filename]

    # Remove file from upload directory
    file_path = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    # Re-index remaining documents
    if processed_documents:
        rag_engine.index_documents(processed_documents)
    else:
        rag_engine.clear_index()

    return {"message": f"Document '{filename}' deleted successfully"}


if __name__ == "__main__":
    import uvicorn
    from config import BACKEND_HOST, BACKEND_PORT

    print(f"Starting RAG Backend Server on {BACKEND_HOST}:{BACKEND_PORT}")
    print(f"Upload directory: {UPLOAD_DIR}")
    print(f"Groq API Key configured: {bool(GROQ_API_KEY)}")
    print(f"Llama Cloud API Key configured: {bool(LLAMA_CLOUD_API_KEY)}")

    uvicorn.run(app, host=BACKEND_HOST, port=BACKEND_PORT)
