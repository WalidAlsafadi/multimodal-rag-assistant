import io
import logging
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend import main
from backend.utils import document_processor
from backend.utils.document_processor import DocumentProcessor
from backend.utils.rag_engine import AnswerGenerationError, RAGEngine


class FakeProcessor:
    def process_file(self, file_path: Path, document_id: str, filename: str):
        assert file_path.name == f"{document_id}.pdf"
        return {
            "document": {
                "id": document_id,
                "filename": filename,
                "file_type": "pdf",
                "pages": 1,
                "text_items": 1,
                "visual_items": 0,
            },
            "items": [
                {
                    "text": "A retrieved passage about revenue growth.",
                    "metadata": {
                        "document_id": document_id,
                        "filename": filename,
                        "file_type": "pdf",
                        "page": 1,
                        "content_type": "text",
                    },
                }
            ],
            "warnings": [],
        }


class FakeRAG:
    def __init__(self):
        self.rebuild_calls = 0
        self.last_items = []
        self.cleared = False

    def rebuild_index(self, items):
        self.rebuild_calls += 1
        self.last_items = list(items)

    def clear_index(self):
        self.cleared = True
        self.last_items = []

    def query(self, question):
        return {
            "answer": f"Answer for {question}",
            "sources": [
                {
                    "document_id": "doc-1",
                    "filename": "report.pdf",
                    "page": 1,
                    "content_type": "text",
                    "snippet": "A retrieved passage.",
                    "score": 0.82,
                }
            ],
        }


@pytest.fixture()
def client(monkeypatch, tmp_path):
    fake_rag = FakeRAG()
    monkeypatch.setattr(main, "UPLOAD_DIR", tmp_path)
    monkeypatch.setattr(main, "doc_processor", FakeProcessor())
    monkeypatch.setattr(main, "rag_engine", fake_rag)
    main.documents.clear()
    yield TestClient(main.app)
    main.documents.clear()


def upload_pdf(client, name="../report.pdf"):
    return client.post("/upload", files={"file": (name, b"%PDF-1.4 fake", "application/pdf")})


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["application"] == "InsightLens"
    assert response.json()["documents"] == 0


def test_unsupported_extension_rejection(client):
    response = client.post("/upload", files={"file": ("notes.doc", b"old word", "application/msword")})
    assert response.status_code == 400
    assert "Unsupported file format" in response.json()["detail"]


def test_empty_question_rejection(client):
    upload_pdf(client)
    response = client.post("/ask", json={"question": "   "})
    assert response.status_code == 400


def test_ask_before_upload(client):
    response = client.post("/ask", json={"question": "What is inside?"})
    assert response.status_code == 400
    assert "Upload" in response.json()["detail"]


def test_safe_filename_handling(client):
    response = upload_pdf(client)
    assert response.status_code == 200
    document = response.json()["document"]
    assert document["filename"] == "report.pdf"
    assert document["id"] in main.documents


def test_filename_control_characters_are_sanitized(client):
    response = upload_pdf(client, name="bad<script>.pdf")
    assert response.status_code == 200
    assert response.json()["document"]["filename"] == "bad_script_.pdf"


def test_content_type_mismatch_rejection(client):
    response = client.post("/upload", files={"file": ("fake.pdf", b"not a pdf", "application/pdf")})
    assert response.status_code == 400
    assert "content does not match" in response.json()["detail"]


def test_upload_size_rejection(client, monkeypatch):
    monkeypatch.setattr(main, "MAX_UPLOAD_BYTES", 3)
    response = client.post("/upload", files={"file": ("large.pdf", b"1234", "application/pdf")})
    assert response.status_code == 413


def test_security_headers_are_present(client):
    response = client.get("/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"


def test_document_deletion_rebuilds_index(client):
    upload = upload_pdf(client)
    document_id = upload.json()["document"]["id"]
    response = client.delete(f"/documents/{document_id}")
    assert response.status_code == 200
    assert document_id not in main.documents
    assert main.rag_engine.rebuild_calls == 2


def test_clear_all(client):
    upload_pdf(client)
    response = client.delete("/documents")
    assert response.status_code == 200
    assert main.documents == {}
    assert main.rag_engine.cleared is True


def test_source_response_structure(client):
    upload_pdf(client)
    response = client.post("/ask", json={"question": "What changed?"})
    assert response.status_code == 200
    source = response.json()["sources"][0]
    assert set(source) == {"document_id", "filename", "page", "content_type", "snippet", "score"}


def test_index_rebuild_on_upload(client):
    upload_pdf(client)
    assert main.rag_engine.rebuild_calls == 1
    assert len(main.rag_engine.last_items) == 1


def test_infer_table_like_block_from_pdf_text():
    text = """Some paragraph before the table.
Category Count Percentage
Arabic 42 51.2%
English 25 30.5%
French 15 18.3%
Table 7: Language distribution across collected records.
Another paragraph after the table."""

    inferred_tables = DocumentProcessor()._infer_tables_from_page_text(text)

    assert len(inferred_tables) == 1
    assert "Category Count Percentage" in inferred_tables[0]
    assert "Arabic 42 51.2%" in inferred_tables[0]
    assert "Table 7: Language distribution across collected records." in inferred_tables[0]


class FakePdfImageFile:
    def __init__(self, name="image.png"):
        self.name = name
        self.image = Image.new("RGB", (8, 8), "red")


class FakePdfPage:
    def __init__(self, images=None):
        self.images = images or []


class FakePdfReader:
    def __init__(self, pages):
        self.pages = pages


def test_pdf_embedded_image_extraction_scans_late_pages():
    pages = [FakePdfPage() for _ in range(49)]
    pages.append(FakePdfPage([FakePdfImageFile("late-chart.png")]))

    embedded_images, warnings = DocumentProcessor()._extract_pdf_embedded_images(FakePdfReader(pages), 20)

    assert warnings == []
    assert len(embedded_images) == 1
    assert embedded_images[0].page == 50
    assert embedded_images[0].image_index == 1
    assert embedded_images[0].name == "late-chart.png"


def test_pdf_embedded_image_extraction_limits_total_images():
    pages = [
        FakePdfPage([FakePdfImageFile("page-1-image-1.png"), FakePdfImageFile("page-1-image-2.png")]),
        FakePdfPage([FakePdfImageFile("page-2-image-1.png")]),
    ]

    embedded_images, warnings = DocumentProcessor()._extract_pdf_embedded_images(FakePdfReader(pages), 2)

    assert len(embedded_images) == 2
    assert [image.page for image in embedded_images] == [1, 1]
    assert [image.image_index for image in embedded_images] == [1, 2]
    assert warnings == ["Visual analysis was limited to the first 2 embedded images found in this PDF."]


def test_pdf_embedded_image_extraction_logs_undecodable_images(caplog):
    caplog.set_level(logging.WARNING)
    pages = [FakePdfPage([SimpleNamespace(name="broken-image")])]

    embedded_images, warnings = DocumentProcessor()._extract_pdf_embedded_images(FakePdfReader(pages), 20)

    assert embedded_images == []
    assert "Unable to decode embedded image on page=1 image=1" in caplog.text
    assert warnings == ["1 embedded PDF image(s) could not be decoded."]


def image_blob() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), "blue").save(buffer, format="PNG")
    return buffer.getvalue()


class FakeDocxParagraph:
    def __init__(self, text):
        self.text = text


class FakeDocxRel:
    reltype = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"

    def __init__(self):
        self.target_part = SimpleNamespace(blob=image_blob())


class FakeDocxDocument:
    def __init__(self, image_count):
        self.paragraphs = [FakeDocxParagraph("DOCX intro text.")]
        self.part = SimpleNamespace(rels={f"rId{index}": FakeDocxRel() for index in range(image_count)})


def test_docx_visual_analysis_limits_embedded_images(monkeypatch, tmp_path):
    class DescribingProcessor(DocumentProcessor):
        def __init__(self):
            super().__init__()
            self.described_images = 0

        def _describe_image(self, image, context=""):
            self.described_images += 1
            return f"visual description {self.described_images}"

    monkeypatch.setattr(document_processor, "MAX_VISUAL_IMAGES", 2)
    monkeypatch.setattr(document_processor, "Document", lambda _: FakeDocxDocument(image_count=3))

    processor = DescribingProcessor()
    result = processor._process_docx(tmp_path / "fake.docx", "doc-1", "report.docx")

    visual_items = [item for item in result["items"] if item["metadata"]["content_type"] == "visual"]
    assert processor.described_images == 2
    assert [item["metadata"]["image_index"] for item in visual_items] == [1, 2]
    assert result["document"]["text_items"] == 1
    assert result["warnings"] == [
        "Visual analysis was limited to the first 2 embedded images found in this DOCX."
    ]


def test_rag_reports_answer_model_failure_without_fallback(tmp_path):
    class QuotaError(Exception):
        status_code = 429
        code = "insufficient_quota"

    class FailingClient:
        class Responses:
            def create(self, **kwargs):
                raise QuotaError("quota unavailable")

        responses = Responses()

    class FakeEmbeddingModel:
        def encode(self, texts, normalize_embeddings=True):
            return [[1.0, 0.0] for _ in texts]

    engine = RAGEngine(client=FailingClient(), embedding_model=FakeEmbeddingModel())
    engine.rebuild_index(
        [
            {
                "text": "PDF visual evidence from paper.pdf, page 2: Figure 1 shows a data collection pipeline with post selection, multilingual signal, and deduplication.",
                "metadata": {
                    "document_id": "doc-1",
                    "filename": "paper.pdf",
                    "file_type": "pdf",
                    "page": 2,
                    "content_type": "visual",
                },
            }
        ]
    )

    with pytest.raises(AnswerGenerationError) as exc_info:
        engine.query("what is in the first figure?")

    assert exc_info.value.status_code == 402
    assert "quota or billing" in str(exc_info.value)
