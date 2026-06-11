"""Tests for the deterministic ATS scoring engine."""

from __future__ import annotations

from app.scoring import scan

STRONG_CV = """
Jane Doe
jane.doe@example.com | +1 (555) 123-4567 | linkedin.com/in/janedoe

Professional Summary
Senior software engineer with 8 years building scalable backend systems.

Work Experience
Acme Corp — Senior Software Engineer
- Led a team of 6 engineers and delivered a payments platform serving 2M users.
- Reduced API latency by 45% by optimizing database queries and adding caching.
- Increased deployment frequency 3x by automating the CI/CD pipeline.
- Cut infrastructure costs by $250k per year through right-sizing services.

Globex — Software Engineer
- Built a data pipeline processing 10M events per day with 99.9% uptime.
- Mentored 4 junior engineers and improved code review turnaround by 30%.

Education
B.S. in Computer Science, State University

Skills
Python, FastAPI, PostgreSQL, Docker, Kubernetes, AWS, React, TypeScript
"""

WEAK_CV = """
John Smith

I am a hard worker and a team player looking for a dynamic role.

Experience
Was responsible for various tasks. Worked on different projects and helped with
many things. Duties included answering emails and attending meetings. I was
involved in some projects and assisted with reports.
"""


def test_strong_cv_scores_high():
    result = scan(STRONG_CV)
    assert result.overall_score >= 75
    assert result.rating in ("Good", "Excellent")
    assert result.stats["action_verbs"] >= 5
    assert result.stats["quantified_bullets"] >= 3


def test_weak_cv_scores_low_and_has_fixes():
    result = scan(WEAK_CV)
    assert result.overall_score < 60
    assert len(result.top_fixes) > 0
    categories = {c.key: c for c in result.categories}
    assert categories["language"].score < 100  # weak phrases / buzzwords penalized


def test_contact_detection():
    result = scan(STRONG_CV)
    contact = next(c for c in result.categories if c.key == "contact")
    assert contact.score == 100


def test_missing_contact_flagged():
    result = scan(WEAK_CV)
    contact = next(c for c in result.categories if c.key == "contact")
    assert contact.score < 100
    assert any(r.category == "contact" for r in result.recommendations)


def test_job_description_adds_keyword_category():
    jd = "We need a Python engineer with FastAPI, PostgreSQL and Kubernetes."
    result = scan(STRONG_CV, jd)
    keys = {c.key for c in result.categories}
    assert "keywords" in keys
    assert "python" in [k.lower() for k in result.matched_keywords]


def test_keyword_miss_detected():
    jd = "Looking for expertise in Rust, Go, Terraform and GraphQL."
    result = scan(STRONG_CV, jd)
    assert len(result.missing_keywords) > 0
    kw = next(c for c in result.categories if c.key == "keywords")
    assert kw.score < 100


def test_scores_are_bounded():
    for cv in (STRONG_CV, WEAK_CV):
        result = scan(cv)
        assert 0 <= result.overall_score <= 100
        for c in result.categories:
            assert 0 <= c.score <= 100
