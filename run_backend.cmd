@echo off
setlocal
cd /d "%~dp0"

echo Starting InsightLens backend on http://localhost:8000
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload

