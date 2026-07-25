#!/usr/bin/env python3
"""
Script to run the Streamlit frontend.
Usage: python run_frontend.py
"""
import os
import sys
import subprocess

def check_dependencies():
    """Check if required dependencies are installed."""
    try:
        import streamlit
        import requests
        print(" All required frontend dependencies are installed.")
        return True
    except ImportError as e:
        print(f" Missing dependency: {e}")
        print("\nPlease install dependencies first:")
        print("  pip install -r requirements.txt")
        return False

def check_backend():
    """Check if backend is running."""
    import requests
    try:
        response = requests.get("http://localhost:8000/", timeout=5)
        if response.status_code == 200:
            print(" Backend is running on http://localhost:8000")
            return True
    except:
        pass

    print("  Warning: Backend does not appear to be running on http://localhost:8000")
    print("   Please start the backend first with: python run_backend.py")
    return False

def main():
    print("=" * 60)
    print(" RAG Project - Frontend (Streamlit)")
    print("=" * 60)

    # Check dependencies
    if not check_dependencies():
        sys.exit(1)

    print()

    # Check backend
    check_backend()

    print()
    print("-" * 60)
    print("Starting Streamlit frontend...")
    print("-" * 60)
    print()

    frontend_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "frontend", "app.py"
    )

    print(f" Frontend will be available at: http://localhost:8501")
    print()
    print("Press Ctrl+C to stop the server.")
    print()

    cmd = [
        sys.executable, "-m", "streamlit", "run",
        frontend_file,
        "--server.port", "8501",
        "--server.address", "localhost",
    ]

    try:
        subprocess.run(cmd, cwd=os.path.dirname(os.path.abspath(__file__)))
    except KeyboardInterrupt:
        print("\n\n Frontend stopped.")
        sys.exit(0)

if __name__ == "__main__":
    main()
