"""Smoke tests for the FastAPI endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

SAMPLE_CV = b"""
Jane Doe
jane.doe@example.com | +1 (555) 123-4567 | linkedin.com/in/janedoe

Professional Summary
Senior engineer with strong delivery record.

Work Experience
- Led a team and delivered a platform serving 2M users.
- Reduced latency by 45% and cut costs by $250k per year.
- Built pipelines processing 10M events per day.

Education
B.S. Computer Science

Skills
Python, FastAPI, PostgreSQL, Docker, Kubernetes
"""


def test_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_scan_endpoint_returns_score():
    files = {"file": ("resume.txt", SAMPLE_CV, "text/plain")}
    res = client.post("/api/scan", files=files)
    assert res.status_code == 200
    body = res.json()
    assert 0 <= body["overall_score"] <= 100
    assert "categories" in body and len(body["categories"]) >= 7
    assert body["meta"]["job_description_provided"] is False


def test_scan_with_job_description():
    files = {"file": ("resume.txt", SAMPLE_CV, "text/plain")}
    data = {"job_description": "Python engineer with FastAPI and Kubernetes."}
    res = client.post("/api/scan", files=files, data=data)
    assert res.status_code == 200
    body = res.json()
    assert body["meta"]["job_description_provided"] is True
    assert any(c["key"] == "keywords" for c in body["categories"])


def test_unsupported_file_type_rejected():
    files = {"file": ("resume.exe", b"binary", "application/octet-stream")}
    res = client.post("/api/scan", files=files)
    assert res.status_code == 415


def test_empty_or_tiny_file_rejected():
    files = {"file": ("resume.txt", b"too short", "text/plain")}
    res = client.post("/api/scan", files=files)
    assert res.status_code == 422
