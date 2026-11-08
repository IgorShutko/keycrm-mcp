@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo [keycrm-mcp] .venv not found, creating...
  uv venv .venv || python -m venv .venv
  uv pip install --python .venv\Scripts\python.exe -r requirements.txt || .venv\Scripts\python.exe -m pip install -r requirements.txt
)
".venv\Scripts\python.exe" server.py %*
