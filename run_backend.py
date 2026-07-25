#!/usr/bin/env python3
"""
Script to run the FastAPI backend server.
Usage: python run_backend.py
"""
import os
import sys
import subprocess

# Add backend to path
backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
sys.path.insert(0, backend_dir)

def check_dependencies():
    """Check if required dependencies are installed."""
    try:
        import fastapi
        import uvicorn
        import llama_index
        import chromadb
        import google.generativeai
        print(" All required dependencies are installed.")
        return True
    except ImportError as e:
        print(f" Missing dependency: {e}")
        print("\nPlease install dependencies first:")
        print("  pip install -r requirements.txt")
        return False

def check_api_keys():
    """Check if API keys are configured."""
    from dotenv import load_dotenv
    load_dotenv()

    google_key = os.getenv("GROQ_API_KEY")
    llama_key = os.getenv("LLAMA_CLOUD_API_KEY")

    if not google_key:
        print("!!  Warning: GROQ_API_KEY not set. Image analysis and RAG will not work.")
        print("   Get your key from: https://groq.com/developers/")
    else:
        print(" GROQ_API_KEY is configured.")

    if not llama_key:
        print("!!  Warning: LLAMA_CLOUD_API_KEY not set. Advanced PDF parsing disabled.")
        print("   Get your key from: https://cloud.llamaindex.ai/")
    else:
        print(" LLAMA_CLOUD_API_KEY is configured.")

    return True

def main():
    print("=" * 60)
    print(" RAG Project - Backend Server")
    print("=" * 60)

    # Check dependencies
    if not check_dependencies():
        sys.exit(1)

    print()

    # Check API keys
    check_api_keys()

    print()
    print("-" * 60)
    print("Starting FastAPI server...")
    print("-" * 60)
    print()

    # Run the server
    from backend.config import BACKEND_HOST, BACKEND_PORT

    print(f" Server will be available at: http://{BACKEND_HOST}:{BACKEND_PORT}")
    print(f" API Documentation: http://{BACKEND_HOST}:{BACKEND_PORT}/docs")
    print()
    print("Press Ctrl+C to stop the server.")
    print()

    # Use subprocess to run uvicorn to avoid import issues
    cmd = [
        sys.executable, "-m", "uvicorn",
        "backend.main:app",
        "--host", BACKEND_HOST,
        "--port", str(BACKEND_PORT),
        "--reload",
    ]

    try:
        subprocess.run(cmd, cwd=os.path.dirname(os.path.abspath(__file__)))
    except KeyboardInterrupt:
        print("\n\n Server stopped.")
        sys.exit(0)

if __name__ == "__main__":
    main()
