"""
RAG (Retrieval-Augmented Generation) Engine.
Handles vector storage, document chunking, and question answering.
"""
import os
from typing import List, Dict, Any, Optional
from pathlib import Path

from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    StorageContext,
    Settings,
    Document as LlamaDocument,
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.groq import Groq
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_parse import LlamaParse
import chromadb

from config import (
    GROQ_API_KEY,
    LLAMA_CLOUD_API_KEY,
    VECTORSTORE_DIR,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    TOP_K_RESULTS,
)


class RAGEngine:
    """RAG engine for document indexing and question answering."""

    def __init__(self):
        self.vectorstore_dir = VECTORSTORE_DIR
        os.makedirs(self.vectorstore_dir, exist_ok=True)

        # Initialize Groq models
        self.embed_model = HuggingFaceEmbedding(
            model_name="BAAI/bge-small-en-v1.5"
        )        
        
        self.llm = Groq(
        model="llama-3.3-70b-versatile", 
        api_key=GROQ_API_KEY
    )

        # Configure LlamaIndex settings
        Settings.embed_model = self.embed_model
        Settings.llm = self.llm
        Settings.node_parser = SentenceSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
        )

        # Initialize ChromaDB
        self.chroma_client = chromadb.PersistentClient(path=self.vectorstore_dir)
        self.collection = self.chroma_client.get_or_create_collection("rag_documents")
        self.vector_store = ChromaVectorStore(chroma_collection=self.collection)
        self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)

        self.index = None
        self.query_engine = None

    def index_documents(self, documents: List[Dict[str, Any]]) -> bool:
        """
        Index documents for RAG retrieval.

        Args:
            documents: List of document dictionaries with 'text' and 'metadata'

        Returns:
            True if indexing successful
        """
        try:
            llama_docs = []
            for doc in documents:
                llama_doc = LlamaDocument(
                    text=doc.get("text", ""),
                    metadata=doc.get("metadata", {}),
                )
                llama_docs.append(llama_doc)

            # Build index
            self.index = VectorStoreIndex.from_documents(
                llama_docs,
                storage_context=self.storage_context,
            )

            # Create query engine
            self.query_engine = self.index.as_query_engine(
                similarity_top_k=TOP_K_RESULTS,
                response_mode="compact",
            )

            return True
        except Exception as e:
            print(f"Error indexing documents: {e}")
            return False

    def index_from_directory(self, directory: str) -> bool:
        """
        Index all supported documents from a directory.
        Uses LlamaParse for PDFs if API key is available.

        Args:
            directory: Path to directory containing documents

        Returns:
            True if indexing successful
        """
        try:
            file_extractor = {}

            # Use LlamaParse for PDFs if API key available
            if LLAMA_CLOUD_API_KEY:
                parser = LlamaParse(
                    api_key=LLAMA_CLOUD_API_KEY,
                    result_type="markdown",
                    verbose=True,
                )
                file_extractor = {".pdf": parser}

            reader = SimpleDirectoryReader(
                directory,
                file_extractor=file_extractor,
            )
            documents = reader.load_data()

            self.index = VectorStoreIndex.from_documents(
                documents,
                storage_context=self.storage_context,
            )

            self.query_engine = self.index.as_query_engine(
                similarity_top_k=TOP_K_RESULTS,
                response_mode="compact",
            )

            return True
        except Exception as e:
            print(f"Error indexing from directory: {e}")
            return False

    def query(self, question: str) -> Dict[str, Any]:
        """
        Answer a question using RAG.

        Args:
            question: User question

        Returns:
            Dictionary with answer and source information
        """
        if not self.query_engine:
            return {
                "answer": "No documents have been indexed yet. Please upload a document first.",
                "sources": [],
            }

        try:
            response = self.query_engine.query(question)

            # Extract source nodes
            sources = []
            if hasattr(response, "source_nodes"):
                for node in response.source_nodes:
                    sources.append({
                        "text": node.text[:500] + "..." if len(node.text) > 500 else node.text,
                        "score": float(node.score) if hasattr(node, "score") else None,
                        "metadata": node.metadata,
                    })

            return {
                "answer": str(response),
                "sources": sources,
            }
        except Exception as e:
            return {
                "answer": f"Error generating answer: {str(e)}",
                "sources": [],
            }

    def clear_index(self) -> bool:
        """Clear the current index and vector store."""
        try:
            self.chroma_client.delete_collection("rag_documents")
            self.collection = self.chroma_client.get_or_create_collection("rag_documents")
            self.vector_store = ChromaVectorStore(chroma_collection=self.collection)
            self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
            self.index = None
            self.query_engine = None
            return True
        except Exception as e:
            print(f"Error clearing index: {e}")
            return False
