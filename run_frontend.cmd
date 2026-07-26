@echo off
setlocal
cd /d "%~dp0frontend"

echo Starting InsightLens frontend on http://localhost:5173
npm run dev

