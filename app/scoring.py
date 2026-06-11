"""Rule-based + lightweight-NLP ATS scoring engine.

The engine is fully deterministic: every category produces a 0-100 sub-score and
a set of recommendations from explicit, auditable rules. The weighted sum of the
sub-scores is the overall ATS score (0-100).
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

from .data import (
    ACTION_VERBS,
    BUZZWORDS,
    OPTIONAL_SECTIONS,
    SECTION_SYNONYMS,
    STOPWORDS,
    WEAK_PHRASES,
)

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(
    r"(?<!\w)(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?){2,4}\d{2,4}(?!\w)"
)
LINKEDIN_RE = re.compile(r"linkedin\.com/in/[\w-]+", re.IGNORECASE)
URL_RE = re.compile(r"https?://[^\s)]+|www\.[^\s)]+", re.IGNORECASE)
NUMBER_RE = re.compile(r"(?<!\w)(?:\$|€|£)?\d[\d,]*(?:\.\d+)?\s?(?:%|k|m|bn|x)?", re.IGNORECASE)
QUANT_RE = re.compile(
    r"(?:\$|€|£)\s?\d|\d[\d,]*(?:\.\d+)?\s?(?:%|percent|k|m|bn|x|hours?|users?|"
    r"customers?|clients?|projects?|people|members?|years?|months?|million|billion)",
    re.IGNORECASE,
)
WORD_RE = re.compile(r"[A-Za-z][A-Za-z+#.\-]{1,}")
BULLET_RE = re.compile(r"^\s*(?:[-*•▪◦‣·]|\d+[.)])\s+", re.MULTILINE)

# Severity ordering for sorting the "top things to fix" list.
_SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}


@dataclass
class Recommendation:
    category: str
    severity: str  # critical | high | medium | low
    message: str


@dataclass
class CategoryResult:
    key: str
    label: str
    score: int  # 0-100 within the category
    weight: float
    status: str  # good | warning | poor
    summary: str
    details: list[str] = field(default_factory=list)


@dataclass
class ScanResult:
    overall_score: int
    rating: str
    summary: str
    categories: list[CategoryResult]
    recommendations: list[Recommendation]
    top_fixes: list[Recommendation]
    stats: dict[str, int]
    matched_keywords: list[str]
    missing_keywords: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def _status_from_score(score: int) -> str:
    if score >= 80:
        return "good"
    if score >= 55:
        return "warning"
    return "poor"


def _tokens(text: str) -> list[str]:
    return [m.group(0).lower() for m in WORD_RE.finditer(text)]


def _find_sections(text: str) -> dict[str, bool]:
    lowered = text.lower()
    lines = [ln.strip() for ln in lowered.splitlines()]
    found: dict[str, bool] = {}
    for canonical, variants in SECTION_SYNONYMS.items():
        present = False
        for variant in variants:
            # A header is a short line that is (or starts with) the section name.
            for ln in lines:
                stripped = ln.strip(" :*#-").strip()
                if stripped == variant or stripped.startswith(variant + " "):
                    if len(stripped.split()) <= 5:
                        present = True
                        break
            if present:
                break
            # Fall back to a loose contains-check for skills/experience etc.
            if re.search(rf"\b{re.escape(variant)}\b", lowered):
                present = True
                break
        found[canonical] = present
    return found


# --------------------------------------------------------------------------- #
# Individual category scorers
# --------------------------------------------------------------------------- #
def _score_contact(text: str, recs: list[Recommendation]) -> CategoryResult:
    has_email = bool(EMAIL_RE.search(text))
    has_phone = bool(PHONE_RE.search(text))
    has_linkedin = bool(LINKEDIN_RE.search(text))
    has_url = bool(URL_RE.search(text)) or has_linkedin

    score = 0
    score += 45 if has_email else 0
    score += 35 if has_phone else 0
    score += 20 if has_url else 0

    details = [
        f"Email: {'found' if has_email else 'missing'}",
        f"Phone number: {'found' if has_phone else 'missing'}",
        f"LinkedIn / portfolio URL: {'found' if has_url else 'missing'}",
    ]
    if not has_email:
        recs.append(
            Recommendation(
                "contact",
                "critical",
                "Add a professional email address — ATS systems key off it to "
                "build your candidate profile.",
            )
        )
    if not has_phone:
        recs.append(
            Recommendation(
                "contact",
                "high",
                "Add a phone number so recruiters and the ATS have a reachable "
                "contact field.",
            )
        )
    if not has_url:
        recs.append(
            Recommendation(
                "contact",
                "medium",
                "Add a LinkedIn URL or portfolio link to strengthen your contact "
                "section.",
            )
        )
    return CategoryResult(
        key="contact",
        label="Contact information",
        score=score,
        weight=12.0,
        status=_status_from_score(score),
        summary="Recruiters and ATS parsers need email, phone and a profile link.",
        details=details,
    )


def _score_sections(text: str, recs: list[Recommendation]) -> CategoryResult:
    found = _find_sections(text)
    required = [k for k in SECTION_SYNONYMS if k not in OPTIONAL_SECTIONS]
    present_required = [k for k in required if found.get(k)]
    score = round(100 * len(present_required) / len(required))
    # Reward an optional summary/profile section.
    if found.get("summary"):
        score = min(100, score + 6)

    details = [
        f"{name.capitalize()}: {'present' if found.get(name) else 'missing'}"
        for name in SECTION_SYNONYMS
    ]
    for name in required:
        if not found.get(name):
            recs.append(
                Recommendation(
                    "sections",
                    "high",
                    f"Add a clearly labelled '{name.capitalize()}' section — ATS "
                    "parsers rely on standard headers to categorise your resume.",
                )
            )
    if not found.get("summary"):
        recs.append(
            Recommendation(
                "sections",
                "low",
                "Consider a short professional summary at the top to frame your "
                "experience for the role.",
            )
        )
    return CategoryResult(
        key="sections",
        label="Standard sections",
        score=score,
        weight=16.0,
        status=_status_from_score(score),
        summary="Use standard headers (Experience, Education, Skills) so the ATS "
        "can map your resume.",
        details=details,
    )


def _score_action_verbs(
    bullets: list[str], tokens: list[str], recs: list[Recommendation]
) -> CategoryResult:
    verb_hits = sum(1 for t in tokens if t in ACTION_VERBS)
    unique_verbs = {t for t in tokens if t in ACTION_VERBS}
    bullet_count = max(len(bullets), 1)
    # Ratio of strong verbs to bullet points, capped at 1.
    ratio = min(1.0, verb_hits / bullet_count) if bullets else min(1.0, verb_hits / 12)
    score = round(100 * ratio)

    details = [
        f"Strong action verbs used: {verb_hits} ({len(unique_verbs)} unique)",
        f"Bullet points detected: {len(bullets)}",
    ]
    if score < 55:
        recs.append(
            Recommendation(
                "action_verbs",
                "high",
                "Start bullet points with strong action verbs (e.g. led, built, "
                "increased, optimized) instead of passive phrasing.",
            )
        )
    elif score < 80:
        recs.append(
            Recommendation(
                "action_verbs",
                "medium",
                "Vary and strengthen your action verbs — a few bullets still read "
                "passively.",
            )
        )
    return CategoryResult(
        key="action_verbs",
        label="Action verbs",
        score=score,
        weight=14.0,
        status=_status_from_score(score),
        summary="Accomplishment-driven bullets that open with strong verbs read "
        "better to recruiters.",
        details=details,
    )


def _score_quantified(
    bullets: list[str], text: str, recs: list[Recommendation]
) -> CategoryResult:
    quant_matches = QUANT_RE.findall(text)
    quant_count = len(quant_matches)
    bullet_count = max(len(bullets), 1)
    quant_bullets = sum(1 for b in bullets if QUANT_RE.search(b))
    ratio = (quant_bullets / bullet_count) if bullets else min(1.0, quant_count / 8)
    # Target ~40% of bullets carrying a metric for a full score.
    score = round(min(100, (ratio / 0.4) * 100))

    details = [
        f"Bullets with measurable results: {quant_bullets} of {len(bullets)}",
        f"Total numeric/metric mentions: {quant_count}",
    ]
    if score < 55:
        recs.append(
            Recommendation(
                "quantified",
                "high",
                "Quantify your impact — add numbers, %, $ or scale (e.g. 'cut build "
                "time 35%', 'managed $2M budget') to your achievements.",
            )
        )
    elif score < 80:
        recs.append(
            Recommendation(
                "quantified",
                "medium",
                "Add metrics to more bullet points; aim for measurable results in "
                "roughly 40% of them.",
            )
        )
    return CategoryResult(
        key="quantified",
        label="Quantified achievements",
        score=score,
        weight=16.0,
        status=_status_from_score(score),
        summary="Numbers prove impact and make accomplishments concrete.",
        details=details,
    )


def _score_formatting(
    text: str, bullets: list[str], recs: list[Recommendation]
) -> CategoryResult:
    score = 100
    details: list[str] = []

    if not bullets:
        score -= 35
        details.append("No bullet points detected — use bullets, not paragraphs.")
        recs.append(
            Recommendation(
                "formatting",
                "high",
                "Use bullet points for your experience instead of dense "
                "paragraphs — they parse and scan far better.",
            )
        )
    else:
        details.append(f"Bullet points detected: {len(bullets)}")

    # Tables / columns frequently break ATS parsing; detect tab-separated columns.
    tabbed_lines = sum(1 for ln in text.splitlines() if "\t" in ln or "  |  " in ln)
    if tabbed_lines >= 5:
        score -= 15
        details.append("Possible tables/columns detected — these can confuse ATS parsers.")
        recs.append(
            Recommendation(
                "formatting",
                "medium",
                "Avoid tables, text boxes and multi-column layouts — many ATS "
                "parsers read them out of order or drop them entirely.",
            )
        )

    # Email present but as part of a header image is impossible to detect; instead
    # flag overly long lines (often a sign of wrapped multi-column extraction).
    long_lines = sum(1 for ln in text.splitlines() if len(ln) > 200)
    if long_lines >= 3:
        score -= 10
        details.append("Several very long lines detected — check column/layout exports.")

    # Excessive non-standard characters can indicate fancy glyphs/icons.
    weird = len(re.findall(r"[^\x00-\x7f]", text))
    if weird > 40:
        score -= 10
        details.append(f"{weird} non-standard characters found (icons/symbols).")
        recs.append(
            Recommendation(
                "formatting",
                "low",
                "Reduce decorative icons/symbols and special characters — stick to "
                "standard text the ATS can read.",
            )
        )

    score = max(0, score)
    return CategoryResult(
        key="formatting",
        label="ATS-friendly formatting",
        score=score,
        weight=15.0,
        status=_status_from_score(score),
        summary="Simple, single-column, bulleted layouts parse most reliably.",
        details=details,
    )


def _score_length(word_count: int, recs: list[Recommendation]) -> CategoryResult:
    if 400 <= word_count <= 850:
        score = 100
    elif word_count < 400:
        score = max(20, round(100 * word_count / 400))
        recs.append(
            Recommendation(
                "length",
                "medium",
                f"Your resume is short ({word_count} words). Add more detail on "
                "achievements and skills — aim for ~400-800 words.",
            )
        )
    else:  # too long
        over = word_count - 850
        score = max(35, 100 - round(over / 20))
        recs.append(
            Recommendation(
                "length",
                "low",
                f"Your resume is long ({word_count} words). Trim to the most "
                "relevant content — aim for ~400-800 words (1-2 pages).",
            )
        )
    return CategoryResult(
        key="length",
        label="Length",
        score=score,
        weight=9.0,
        status=_status_from_score(score),
        summary="Most resumes are strongest at 1-2 pages (~400-800 words).",
        details=[f"Word count: {word_count}"],
    )


def _score_language(text: str, recs: list[Recommendation]) -> CategoryResult:
    lowered = text.lower()
    weak_found = sorted({p for p in WEAK_PHRASES if p in lowered})
    buzz_found = sorted({b for b in BUZZWORDS if re.search(rf"\b{re.escape(b)}\b", lowered)})

    score = 100 - 9 * len(weak_found) - 6 * len(buzz_found)
    score = max(0, score)

    details = []
    if weak_found:
        details.append("Weak phrasing: " + ", ".join(weak_found))
    if buzz_found:
        details.append("Clichés/buzzwords: " + ", ".join(buzz_found))
    if not details:
        details.append("No weak phrasing or clichés detected.")

    if weak_found:
        recs.append(
            Recommendation(
                "language",
                "medium",
                "Replace weak phrases like "
                + ", ".join(f"'{p}'" for p in weak_found[:3])
                + " with strong action verbs and concrete results.",
            )
        )
    if buzz_found:
        recs.append(
            Recommendation(
                "language",
                "low",
                "Drop generic buzzwords ("
                + ", ".join(buzz_found[:3])
                + ") in favour of specific, evidenced skills.",
            )
        )
    return CategoryResult(
        key="language",
        label="Language quality",
        score=score,
        weight=8.0,
        status=_status_from_score(score),
        summary="Avoid passive phrasing and clichés; lead with concrete results.",
        details=details,
    )


def _extract_jd_keywords(job_description: str, limit: int = 25) -> list[str]:
    counts: dict[str, int] = {}
    for tok in _tokens(job_description):
        cleaned = tok.strip(".-")
        if len(cleaned) < 3 or cleaned in STOPWORDS:
            continue
        counts[cleaned] = counts.get(cleaned, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return [w for w, _ in ranked[:limit]]


def _score_keywords(
    text: str, job_description: str, recs: list[Recommendation]
) -> tuple[CategoryResult, list[str], list[str]]:
    keywords = _extract_jd_keywords(job_description)
    resume_tokens = set(_tokens(text))
    matched = [k for k in keywords if k in resume_tokens]
    missing = [k for k in keywords if k not in resume_tokens]
    if keywords:
        score = round(100 * len(matched) / len(keywords))
    else:
        score = 0

    details = [
        f"Job-description keywords matched: {len(matched)} of {len(keywords)}",
    ]
    if missing:
        if score < 55:
            severity = "critical"
        elif score < 80:
            severity = "high"
        else:
            severity = "medium"
        recs.append(
            Recommendation(
                "keywords",
                severity,
                "Naturally weave in missing role keywords where you genuinely have "
                "the experience: " + ", ".join(missing[:8]) + ".",
            )
        )
    return (
        CategoryResult(
            key="keywords",
            label="Job-description keyword match",
            score=score,
            weight=22.0,
            status=_status_from_score(score),
            summary="ATS ranking is driven by how well your resume matches the job "
            "description's keywords.",
            details=details,
        ),
        matched,
        missing,
    )


def _rating(score: int) -> str:
    if score >= 85:
        return "Excellent"
    if score >= 70:
        return "Good"
    if score >= 50:
        return "Needs work"
    return "Poor"


def scan(text: str, job_description: str | None = None) -> ScanResult:
    """Run all scoring rules over the extracted CV text.

    If ``job_description`` is provided, keyword matching is added and weighted
    heavily, mirroring how a real ATS ranks against a specific posting.
    """
    job_description = (job_description or "").strip()
    recs: list[Recommendation] = []
    tokens = _tokens(text)
    word_count = len(text.split())
    bullets = [b.strip() for b in BULLET_RE.split(text) if b.strip()]
    # BULLET_RE.split keeps text between markers; recompute bullet lines instead.
    bullets = [
        ln.strip()
        for ln in text.splitlines()
        if BULLET_RE.match(ln) and len(ln.strip()) > 2
    ]

    categories: list[CategoryResult] = [
        _score_contact(text, recs),
        _score_sections(text, recs),
        _score_action_verbs(bullets, tokens, recs),
        _score_quantified(bullets, text, recs),
        _score_formatting(text, bullets, recs),
        _score_length(word_count, recs),
        _score_language(text, recs),
    ]

    matched_keywords: list[str] = []
    missing_keywords: list[str] = []
    if job_description:
        kw_result, matched_keywords, missing_keywords = _score_keywords(
            text, job_description, recs
        )
        categories.append(kw_result)

    total_weight = sum(c.weight for c in categories)
    overall = round(sum(c.score * c.weight for c in categories) / total_weight)

    recs.sort(key=lambda r: _SEVERITY_RANK.get(r.severity, 99))
    top_fixes = [r for r in recs if r.severity in ("critical", "high")][:5]
    if not top_fixes:
        top_fixes = recs[:3]

    rating = _rating(overall)
    if overall >= 85:
        summary = "Strong, ATS-friendly resume. A few tweaks will make it shine."
    elif overall >= 70:
        summary = "Solid resume with a good ATS foundation — address the items below to stand out."
    elif overall >= 50:
        summary = "Your resume needs work to reliably pass ATS screening. Focus on the top fixes."
    else:
        summary = "This resume will struggle with ATS screening. Tackle the critical fixes first."

    stats = {
        "word_count": word_count,
        "bullet_points": len(bullets),
        "action_verbs": sum(1 for t in tokens if t in ACTION_VERBS),
        "quantified_bullets": sum(1 for b in bullets if QUANT_RE.search(b)),
    }

    return ScanResult(
        overall_score=overall,
        rating=rating,
        summary=summary,
        categories=categories,
        recommendations=recs,
        top_fixes=top_fixes,
        stats=stats,
        matched_keywords=matched_keywords,
        missing_keywords=missing_keywords,
    )
