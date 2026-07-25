"""
Streamlit Frontend for RAG Project.
Provides a user-friendly interface for uploading documents and asking questions.
"""
import os
import requests
import json
from pathlib import Path

import streamlit as st
from PIL import Image

# Configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Page configuration
st.set_page_config(
    page_title="RAG Document Q&A",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .answer-box {
        background-color: transparent;
        border-left: 4px solid #1f77b4;
        padding: 1rem 0 1rem 1rem;
        margin: 1rem 0;
    }
    .source-box {
        background-color: #f9f9f9;
        border: 1px solid #e0e0e0;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .image-analysis-box {
        background-color: #fff8f0;
        border-left: 4px solid #ff9500;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .stButton>button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)


def check_backend():
    """Check if backend is running."""
    try:
        response = requests.get(f"{BACKEND_URL}/", timeout=5)
        return response.status_code == 200
    except:
        return False


def upload_file_to_backend(file):
    """Upload a file to the backend."""
    files = {"file": (file.name, file.getvalue(), file.type)}
    response = requests.post(f"{BACKEND_URL}/upload", files=files, timeout=120)
    return response


def ask_question_backend(question, analyze_images=True):
    """Send a question to the backend."""
    payload = {
        "question": question,
        "analyze_images": analyze_images,
    }
    response = requests.post(
        f"{BACKEND_URL}/ask",
        json=payload,
        timeout=120,
    )
    return response


def get_documents():
    """Get list of uploaded documents."""
    response = requests.get(f"{BACKEND_URL}/documents", timeout=10)
    return response


def clear_all_documents():
    """Clear all documents from backend."""
    response = requests.delete(f"{BACKEND_URL}/documents", timeout=10)
    return response


# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "documents" not in st.session_state:
    st.session_state.documents = []
if "backend_connected" not in st.session_state:
    st.session_state.backend_connected = False


# Sidebar
with st.sidebar:
    # Document Management
    st.header("Documents")

    if st.button("Refresh Document List"):
        with st.spinner("Loading documents..."):
            try:
                response = get_documents()
                if response.status_code == 200:
                    st.session_state.documents = response.json().get("documents", [])
                else:
                    st.error("Failed to fetch documents")
            except Exception as e:
                st.error(f"Error: {e}")

    # Display documents
    if st.session_state.documents:
        st.write(f"**{len(st.session_state.documents)} document(s) loaded:**")
        for doc in st.session_state.documents:
            with st.expander(doc['filename']):
                st.write(f"- Text length: {doc['text_length']} chars")
                st.write(f"- Images: {doc['images_count']}")
                st.json(doc.get("metadata", {}))
    else:
        st.info("No documents uploaded yet")

    if st.session_state.documents:
        if st.button("Clear All Documents", type="secondary"):
            with st.spinner("Clearing documents..."):
                try:
                    response = clear_all_documents()
                    if response.status_code == 200:
                        st.session_state.documents = []
                        st.session_state.messages = []
                        st.success("All documents cleared!")
                        st.rerun()
                    else:
                        st.error("Failed to clear documents")
                except Exception as e:
                    st.error(f"Error: {e}")

    st.divider()

    # Supported formats info
    st.header("Supported Formats")
    st.markdown("""
    - PDF (.pdf)
    - Word (.docx, .doc)
    - Images (.png, .jpg, .jpeg, .bmp, .tiff)
    """)


# Main content
st.markdown('<div class="main-header">RAG Document Q&A</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">'
    'Upload PDF, Word, or Image files and ask questions about their content. '
    '</div>',
    unsafe_allow_html=True
)

# File upload section
st.header("Upload Document")

uploaded_file = st.file_uploader(
    "Choose a file",
    type=["pdf", "docx", "doc", "png", "jpg", "jpeg", "bmp", "tiff"],
    help="Upload a document to analyze",
)

if uploaded_file is not None:
    col1, col2 = st.columns([3, 1])
    with col1:
        st.write(f"**Selected file:** {uploaded_file.name}")
        st.write(f"**Size:** {uploaded_file.size / 1024:.1f} KB")
        st.write(f"**Type:** {uploaded_file.type}")
    with col2:
        if st.button("Upload & Process", type="primary"):
            with st.spinner("Uploading and processing document... This may take a moment."):
                try:
                    response = upload_file_to_backend(uploaded_file)
                    if response.status_code == 200:
                        result = response.json()
                        st.success(result['message'])

                        info = result.get("document_info", {})
                        st.info(
                            f"Extracted {info.get('text_length', 0)} characters of text "
                            f"and found {info.get('images_found', 0)} image(s)."
                        )

                        # Refresh document list
                        doc_response = get_documents()
                        if doc_response.status_code == 200:
                            st.session_state.documents = doc_response.json().get("documents", [])

                        
                    else:
                        error_detail = response.json().get("detail", "Unknown error")
                        st.error(f"Upload failed: {error_detail}")
                except requests.exceptions.ConnectionError:
                    st.error("Cannot connect to backend. Make sure it's running.")
                except Exception as e:
                    st.error(f"Error: {str(e)}")

st.divider()

# Q&A Section
st.header("Ask a Question")

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        # Show sources if available
        if message.get("sources"):
            with st.expander("View Sources"):
                for i, source in enumerate(message["sources"], 1):
                    st.markdown(f"**Source {i}** (Score: {source.get('score', 'N/A'):.3f})")
                    st.markdown(f"```\n{source['text']}\n```")

        # Show image analysis if available
        if message.get("image_analysis"):
            with st.expander("Image Analysis"):
                for img in message["image_analysis"]:
                    st.markdown(f"**From {img['document']}:**")
                    st.markdown(f"> {img['description']}")

# Question input
if question := st.chat_input("Ask something about your documents..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": question})

    with st.chat_message("user"):
        st.markdown(question)

    # Get answer from backend
    with st.chat_message("assistant"):
        with st.spinner("Searching documents and generating answer..."):
            try:
                response = ask_question_backend(question, analyze_images=True)

                if response.status_code == 200:
                    result = response.json()
                    answer = result.get("answer", "No answer generated.")
                    sources = result.get("sources", [])
                    image_analysis = result.get("image_analysis", [])

                    # Display answer
                    st.markdown(f'<div class="answer-box">{answer}</div>', unsafe_allow_html=True)

                    # Display sources
                    if sources:
                        with st.expander("View Sources"):
                            for i, source in enumerate(sources, 1):
                                score = source.get("score")
                                score_text = f"{score:.3f}" if score is not None else "N/A"
                                st.markdown(f"**Source {i}** (Relevance: {score_text})")
                                st.markdown(f"```\n{source['text']}\n```")

                    # Display image analysis
                    if image_analysis:
                        with st.expander("Image Analysis"):
                            for img in image_analysis:
                                st.markdown(f"**From {img['document']}:**")
                                st.markdown(f"> {img['description']}")

                    # Save to session state
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "sources": sources,
                        "image_analysis": image_analysis,
                    })

                else:
                    error_detail = response.json().get("detail", "Unknown error")
                    st.error(f"Error: {error_detail}")
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": f"Error: {error_detail}",
                    })

            except requests.exceptions.ConnectionError:
                error_msg = "Cannot connect to backend. Please make sure the backend server is running."
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg,
                })
            except Exception as e:
                error_msg = f"Error: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg,
                })

# Footer
st.divider()
st.caption(
    "Built with FastAPI + Streamlit + Groq + LlamaIndex | "
    "Supports PDF, Word, and Image files with automatic image analysis"
)
