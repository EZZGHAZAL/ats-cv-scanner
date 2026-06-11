@echo off
REM Convenience launcher for local development on Windows.

if "%HOST%"=="" set HOST=0.0.0.0
if "%PORT%"=="" set PORT=8000

uvicorn app.main:app --host %HOST% --port %PORT% --reload
