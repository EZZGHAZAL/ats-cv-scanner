"""FastAPI application: CV upload + ATS scan endpoints and static frontend."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .parsing import EmptyDocumentError, UnsupportedFileError, parse_cv
from .scoring import scan

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB

app = FastAPI(
    title="ATS CV Scanner",
    description="Scan your CV for ATS-friendliness, get a score and concrete "
    "recommendations to improve it.",
    version=__version__,
)

STATIC_DIR = Path(__file__).parent / "static"


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.post("/api/scan")
async def scan_cv(
    file: UploadFile = File(...),
    job_description: str = Form(default=""),
) -> JSONResponse:
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail="File too large. Please upload a file under 5 MB.",
        )

    try:
        parsed = parse_cv(data, file.filename or "resume")
    except UnsupportedFileError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    except EmptyDocumentError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    result = scan(parsed.text, job_description)
    payload = result.to_dict()
    payload["meta"] = {
        "filename": parsed.filename,
        "file_type": parsed.file_type,
        "job_description_provided": bool(job_description.strip()),
    }
    return JSONResponse(payload)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
