"""
Document processing utilities for extracting text and images from various file formats.
Supports PDF, Word documents, and image files.
"""
import os
import io
import base64
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import json

import PyPDF2
from docx import Document
from PIL import Image
from pdf2image import convert_from_path

# Switched from google.generativeai to groq client
from groq import Groq
from config import GROQ_API_KEY, UPLOAD_DIR


# Configure Groq client if API key is available
groq_client = None
if GROQ_API_KEY:
    groq_client = Groq(api_key=GROQ_API_KEY)


class DocumentProcessor:
    """Handles extraction of text and images from various document formats."""

    def __init__(self):
        self.upload_dir = UPLOAD_DIR
        os.makedirs(self.upload_dir, exist_ok=True)

    def process_file(self, file_path: str) -> Dict[str, Any]:
        """
        Process a file and extract text and image content.

        Args:
            file_path: Path to the uploaded file

        Returns:
            Dictionary containing extracted text, images, and metadata
        """
        ext = Path(file_path).suffix.lower()

        if ext == ".pdf":
            return self._process_pdf(file_path)
        elif ext in [".docx", ".doc"]:
            return self._process_word(file_path)
        elif ext in [".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif"]:
            return self._process_image(file_path)
        else:
            raise ValueError(f"Unsupported file format: {ext}")

    def _process_pdf(self, file_path: str) -> Dict[str, Any]:
        """Extract text and images from PDF."""
        result = {
            "text": "",
            "images": [],
            "metadata": {"type": "pdf", "pages": 0}
        }

        # Extract text using PyPDF2
        with open(file_path, "rb") as f:
            pdf_reader = PyPDF2.PdfReader(f)
            result["metadata"]["pages"] = len(pdf_reader.pages)

            for page_num, page in enumerate(pdf_reader.pages):
                text = page.extract_text()
                if text:
                    result["text"] += f"\n--- Page {page_num + 1} ---\n{text}\n"

        # Extract images using pdf2image
        try:
            images = convert_from_path(file_path, dpi=200)
            for i, image in enumerate(images):
                img_path = os.path.join(
                    self.upload_dir, 
                    f"{Path(file_path).stem}_page_{i+1}.png"
                )
                image.save(img_path, "PNG")
                result["images"].append({
                    "path": img_path,
                    "page": i + 1,
                    "description": None  # Will be filled by image analysis
                })
        except Exception as e:
            print(f"Warning: Could not extract images from PDF: {e}")

        return result

    def _process_word(self, file_path: str) -> Dict[str, Any]:
        """Extract text and images from Word document."""
        result = {
            "text": "",
            "images": [],
            "metadata": {"type": "word", "paragraphs": 0}
        }

        doc = Document(file_path)

        # Extract text
        full_text = []
        for para in doc.paragraphs:
            full_text.append(para.text)
        result["text"] = "\n".join(full_text)
        result["metadata"]["paragraphs"] = len(doc.paragraphs)

        # Extract images
        image_count = 0
        for rel in doc.part.rels.values():
            if "image" in rel.reltype:
                image_count += 1
                image_data = rel.target_part.blob
                img = Image.open(io.BytesIO(image_data))
                img_path = os.path.join(
                    self.upload_dir,
                    f"{Path(file_path).stem}_image_{image_count}.png"
                )
                img.save(img_path)
                result["images"].append({
                    "path": img_path,
                    "index": image_count,
                    "description": None
                })

        result["metadata"]["image_count"] = image_count
        return result

    def _process_image(self, file_path: str) -> Dict[str, Any]:
        """Process a standalone image file."""
        result = {
            "text": "",
            "images": [],
            "metadata": {"type": "image", "filename": Path(file_path).name}
        }

        result["images"].append({
            "path": file_path,
            "index": 1,
            "description": None
        })

        return result

    def analyze_images(self, images: List[Dict[str, Any]], prompt: str = None) -> List[Dict[str, Any]]:
        """
        Analyze images using Gemini vision model.

        Args:
            images: List of image dictionaries with 'path' key
            prompt: Custom prompt for image analysis

        Returns:
            List of image dictionaries with added 'description' field
        """
        if not GROQ_API_KEY or not groq_client:
            print("Warning: GROQ_API_KEY not set. Skipping image analysis.")
            return images

        default_prompt = (
            "Analyze this image in detail. Describe what you see, including any text, "
            "diagrams, charts, tables, or visual elements. Be thorough and specific."
        )
        analysis_prompt = prompt or default_prompt

        for img_info in images:
            try:
                # Encode the local image file to base64 for Groq Vision compatibility
                b64_image = encode_image_to_base64(img_info["path"])
                mime_type = get_image_mime_type(img_info["path"])

                # Request analysis from Groq Llama Vision model
                response = groq_client.chat.completions.create(
                    model="qwen/qwen3.6-27b",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": analysis_prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:{mime_type};base64,{b64_image}"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=1024,
                )
                img_info["description"] = response.choices[0].message.content
            except Exception as e:
                img_info["description"] = f"Error analyzing image: {str(e)}"

        return images


def encode_image_to_base64(image_path: str) -> str:
    """Encode an image to base64 string."""
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")


def get_image_mime_type(image_path: str) -> str:
    """Get MIME type for an image file."""
    ext = Path(image_path).suffix.lower()
    mime_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".bmp": "image/bmp",
        ".tiff": "image/tiff",
        ".tif": "image/tiff",
    }
    return mime_types.get(ext, "image/png")