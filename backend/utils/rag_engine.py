"""Chroma-backed retrieval and grounded OpenAI answer generation."""
from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any

import chromadb
from llama_index.core import Document as LlamaDocument
from llama_index.core.node_parser import SentenceSplitter
from openai import OpenAI

from ..config import (
    ANSWER_MAX_TOKENS,
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    MAX_CONTEXT_CHARS,
    OPENAI_MODEL,
    TOP_K_RESULTS,
    VECTORSTORE_DIR,
    require_openai_api_key,
)

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer


class AnswerGenerationError(Exception):
    """Raised when the hosted answer model cannot generate a response."""

    def __init__(self, message: str, status_code: int = 503):
        super().__init__(message)
        self.status_code = status_code


class RAGEngine:
    """Index evidence items with local embeddings and answer from retrieved context only."""

    def __init__(self, client: OpenAI | None = None, embedding_model: "SentenceTransformer | None" = None):
        self.client = client
        self.embed_model = embedding_model
        self.splitter = SentenceSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
        self.chroma_client = chromadb.PersistentClient(path=str(VECTORSTORE_DIR))
        self.collection_name = "insightlens_session"
        self.collection = self.chroma_client.get_or_create_collection(self.collection_name)
        self.indexed_count = self.collection.count()

    def rebuild_index(self, content_items: list[dict[str, Any]]) -> None:
        """Clear Chroma and rebuild it from active in-memory evidence items."""
        self.clear_index()
        if not content_items:
            return

        ids: list[str] = []
        texts: list[str] = []
        metadatas: list[dict[str, Any]] = []

        for item in content_items:
            document = LlamaDocument(text=item["text"], metadata=item["metadata"])
            for node_index, node in enumerate(self.splitter.get_nodes_from_documents([document])):
                text = node.get_content().strip()
                if not text:
                    continue
                metadata = self._normalize_metadata({**item["metadata"], **node.metadata})
                chunk_hash = hashlib.sha1(
                    f"{metadata.get('document_id')}|{metadata.get('page')}|{metadata.get('content_type')}|{text}".encode(
                        "utf-8"
                    )
                ).hexdigest()
                metadata["chunk_id"] = chunk_hash
                metadata["snippet"] = self._snippet(text, 500)
                ids.append(f"{metadata['document_id']}-{node_index}-{chunk_hash[:12]}")
                texts.append(text)
                metadatas.append(metadata)

        if not texts:
            return

        self.collection.add(
            ids=ids,
            documents=texts,
            embeddings=self._embed(texts),
            metadatas=metadatas,
        )
        self.indexed_count = self.collection.count()

    def query(self, question: str) -> dict[str, Any]:
        if self.collection.count() == 0:
            return {
                "answer": "No documents have been indexed yet. Please upload a document first.",
                "sources": [],
            }

        result_count = min(max(TOP_K_RESULTS * 4, 10), self.collection.count())
        results = self.collection.query(
            query_embeddings=self._embed([question]),
            n_results=result_count,
            include=["documents", "metadatas", "distances"],
        )
        sources = self._sources_from_results(results, question)
        if not sources:
            return {
                "answer": "I could not find relevant evidence in the uploaded content.",
                "sources": [],
            }

        context = self._build_context(sources)
        prompt = (
            "You are InsightLens, a multimodal retrieval assistant. Answer only from the supplied "
            "context. Do not use outside knowledge. If the answer is not available in the uploaded "
            "content, say so clearly. Do not invent filenames, page numbers, facts, or citations. "
            "For questions about figures, charts, percentages, tables, rows, columns, or entries, extract "
            "the requested visible values directly from the context. If a value is marked unreadable, say so. "
            "Be clear and concise, and use Markdown when useful.\n\n"
            f"Question:\n{question}\n\nRetrieved context:\n{context}"
        )
        try:
            response = self._client().responses.create(
                model=OPENAI_MODEL,
                input=prompt,
                max_output_tokens=ANSWER_MAX_TOKENS,
            )
            answer = (getattr(response, "output_text", "") or "").strip()
        except Exception as exc:
            raise AnswerGenerationError(self._public_openai_error_message(exc), self._openai_error_status(exc)) from exc
        if not answer:
            answer = "I could not generate an answer from the retrieved evidence."
        return {"answer": answer, "sources": sources}

    def clear_index(self) -> None:
        try:
            self.chroma_client.delete_collection(self.collection_name)
        except Exception:
            pass
        self.collection = self.chroma_client.get_or_create_collection(self.collection_name)
        self.indexed_count = 0

    def _client(self) -> OpenAI:
        if self.client is None:
            self.client = OpenAI(api_key=require_openai_api_key())
        return self.client

    def _embed(self, texts: list[str]) -> list[list[float]]:
        if self.embed_model is None:
            from sentence_transformers import SentenceTransformer

            self.embed_model = SentenceTransformer("BAAI/bge-small-en-v1.5")
        embeddings = self.embed_model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist() if hasattr(embeddings, "tolist") else embeddings

    def _sources_from_results(self, results: dict[str, Any], question: str) -> list[dict[str, Any]]:
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]
        sources: list[dict[str, Any]] = []
        seen: set[str] = set()

        for text, metadata, distance in zip(documents, metadatas, distances):
            key = metadata.get("chunk_id") or hashlib.sha1(text.encode("utf-8")).hexdigest()
            if key in seen:
                continue
            seen.add(key)
            score = max(0.0, 1.0 - float(distance)) if distance is not None else None
            page = metadata.get("page")
            content_type = metadata.get("content_type")
            boosted_score = self._boost_score(score, text, content_type, question)
            sources.append(
                {
                    "document_id": metadata.get("document_id"),
                    "filename": metadata.get("filename"),
                    "page": int(page) if isinstance(page, int) or (isinstance(page, str) and page.isdigit()) else None,
                    "content_type": content_type,
                    "snippet": self._snippet(text, 500),
                    "context_text": self._snippet(text, 1800),
                    "score": round(score, 4) if score is not None else None,
                    "_rank_score": boosted_score,
                }
            )
        sources.sort(key=lambda source: source["_rank_score"], reverse=True)
        return [{key: value for key, value in source.items() if key != "_rank_score"} for source in sources[:TOP_K_RESULTS]]

    def _build_context(self, sources: list[dict[str, Any]]) -> str:
        blocks: list[str] = []
        total = 0
        for index, source in enumerate(sources, start=1):
            page = f", page {source['page']}" if source.get("page") is not None else ""
            block = (
                f"[Source {index}: {source['filename']}{page}, {source['content_type']}]\n"
                f"{source.get('context_text') or source['snippet']}"
            )
            if total + len(block) > MAX_CONTEXT_CHARS:
                remaining = max(0, MAX_CONTEXT_CHARS - total)
                if remaining:
                    blocks.append(block[:remaining])
                break
            blocks.append(block)
            total += len(block)
        return "\n\n".join(blocks)

    def _normalize_metadata(self, metadata: dict[str, Any]) -> dict[str, Any]:
        normalized = {}
        for key, value in metadata.items():
            if value is None:
                normalized[key] = ""
            elif isinstance(value, (str, int, float, bool)):
                normalized[key] = value
            else:
                normalized[key] = str(value)
        if normalized.get("page") is None:
            normalized["page"] = ""
        return normalized

    def _snippet(self, text: str, limit: int) -> str:
        compact = " ".join(text.split())
        if len(compact) <= limit:
            return compact
        return compact[: limit - 1].rstrip() + "..."

    def _boost_score(self, score: float | None, text: str, content_type: str | None, question: str) -> float:
        boosted = score or 0.0
        haystack = text.lower()
        needle = question.lower()
        if "figure" in needle or "fig" in needle:
            if content_type == "visual":
                boosted += 0.2
            for token in ("figure", "fig.", "fig ", "chart", "pie chart", "caption"):
                if token in haystack:
                    boosted += 0.08
        if self._mentions_table_intent(needle):
            if content_type == "table":
                boosted += 0.25
            for token in ("table", "row", "column", "entry", "entries", "metric", "value", "score", "caption"):
                if token in haystack:
                    boosted += 0.08
        for token in ("percentage", "percent", "%", "language distribution"):
            if token in needle and token in haystack:
                boosted += 0.1
        return boosted

    def _mentions_table_intent(self, question: str) -> bool:
        return any(
            token in question
            for token in (
                "table",
                "tab.",
                "row",
                "column",
                "entry",
                "entries",
                "leaderboard",
                "rank",
                "score",
                "metric",
            )
        )

    def _public_openai_error_message(self, exc: Exception) -> str:
        status_code = getattr(exc, "status_code", None)
        error_code = self._openai_error_code(exc)
        if status_code in {401, 403}:
            return "OpenAI authentication failed. Check the backend OPENAI_API_KEY."
        if status_code in {402, 429} or error_code in {"insufficient_quota", "billing_hard_limit_reached"}:
            return "OpenAI quota or billing is unavailable. Add credits or check usage limits, then try again."
        return "OpenAI answer generation is currently unavailable. Try again after the backend can reach OpenAI."

    def _openai_error_status(self, exc: Exception) -> int:
        status_code = getattr(exc, "status_code", None)
        if status_code in {401, 403}:
            return 401
        if status_code in {402, 429} or self._openai_error_code(exc) in {"insufficient_quota", "billing_hard_limit_reached"}:
            return 402
        return 503

    def _openai_error_code(self, exc: Exception) -> str | None:
        body = getattr(exc, "body", None)
        if isinstance(body, dict):
            error = body.get("error")
            if isinstance(error, dict) and error.get("code"):
                return str(error["code"])
            if body.get("code"):
                return str(body["code"])
        return getattr(exc, "code", None)
