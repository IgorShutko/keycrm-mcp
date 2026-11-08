@echo off
setlocal
cd /d "%~dp0"
set PY=.venv\Scripts\python.exe
if not exist "%PY%" (
  echo [keycrm-mcp] .venv not found, see README
  exit /b 1
)

echo === 1/4 smoke: core tools, CRUD cycle ===
"%PY%" test_smoke.py || exit /b 1

echo === 2/4 domains: finance, delivery, stocks, documents ===
"%PY%" test_domains.py || exit /b 1

echo === 3/4 actions: read-only sweep of every action ===
"%PY%" test_actions.py || exit /b 1

echo === 4/4 account hygiene: counters and MCP TEST leftovers ===
"%PY%" crm_cli.py check

echo All checks finished.
