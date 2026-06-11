"""Static lexicons used by the scoring engine.

Kept in one place so the rules stay deterministic, auditable, and easy to extend.
"""

from __future__ import annotations

# Strong action verbs that signal accomplishment-oriented bullet points.
ACTION_VERBS: frozenset[str] = frozenset(
    {
        "accelerated", "achieved", "acquired", "adapted", "administered", "advanced",
        "advised", "analyzed", "architected", "automated", "boosted", "built",
        "championed", "collaborated", "completed", "conceived", "conducted",
        "consolidated", "constructed", "converted", "coordinated", "created",
        "cut", "decreased", "delivered", "deployed", "designed", "developed",
        "devised", "directed", "doubled", "drove", "earned", "eliminated",
        "enabled", "engineered", "enhanced", "established", "exceeded", "executed",
        "expanded", "expedited", "facilitated", "forecasted", "formulated",
        "founded", "generated", "grew", "guided", "headed", "implemented",
        "improved", "increased", "influenced", "initiated", "innovated",
        "integrated", "introduced", "launched", "led", "leveraged", "maintained",
        "managed", "maximized", "mentored", "migrated", "minimized", "modernized",
        "monitored", "negotiated", "operated", "optimized", "orchestrated",
        "organized", "overhauled", "oversaw", "performed", "pioneered", "planned",
        "produced", "programmed", "promoted", "proposed", "prototyped", "provided",
        "published", "reduced", "refactored", "reengineered", "researched",
        "resolved", "restructured", "revamped", "saved", "scaled", "secured",
        "shipped", "simplified", "solved", "spearheaded", "standardized",
        "streamlined", "strengthened", "supervised", "supported", "surpassed",
        "trained", "transformed", "translated", "tripled", "unified", "upgraded",
        "won",
    }
)

# Weak / vague phrasing that ATS reviewers and recruiters tend to penalize.
WEAK_PHRASES: tuple[str, ...] = (
    "responsible for",
    "duties included",
    "worked on",
    "helped with",
    "assisted with",
    "in charge of",
    "tasked with",
    "involved in",
    "participated in",
    "handled",
)

# Overused buzzwords / clichés that add little signal to a resume.
BUZZWORDS: tuple[str, ...] = (
    "team player",
    "hard worker",
    "hard-working",
    "go-getter",
    "self-starter",
    "detail-oriented",
    "results-driven",
    "results-oriented",
    "think outside the box",
    "synergy",
    "go to market",
    "best of breed",
    "value add",
    "value-add",
    "dynamic",
    "proactive",
    "motivated",
    "passionate",
    "rockstar",
    "ninja",
    "guru",
)

# Section headers commonly expected by ATS parsers. Maps a canonical name to the
# header variants that count as "present".
SECTION_SYNONYMS: dict[str, tuple[str, ...]] = {
    "contact": ("contact", "personal information", "personal details"),
    "summary": (
        "summary",
        "professional summary",
        "profile",
        "objective",
        "about me",
        "career objective",
    ),
    "experience": (
        "experience",
        "work experience",
        "professional experience",
        "employment",
        "employment history",
        "work history",
        "career history",
    ),
    "education": ("education", "academic background", "qualifications"),
    "skills": (
        "skills",
        "technical skills",
        "core competencies",
        "competencies",
        "key skills",
        "areas of expertise",
    ),
}

# Sections that are "nice to have" but not required for a passing score.
OPTIONAL_SECTIONS: frozenset[str] = frozenset({"summary"})

# Very common English words to ignore when extracting keywords from a job
# description, so that the keyword match focuses on meaningful terms.
STOPWORDS: frozenset[str] = frozenset(
    {
        "a", "an", "the", "and", "or", "but", "if", "then", "else", "when",
        "at", "by", "for", "with", "about", "against", "between", "into",
        "through", "during", "before", "after", "above", "below", "to", "from",
        "up", "down", "in", "out", "on", "off", "over", "under", "again",
        "further", "of", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "doing", "will", "would",
        "shall", "should", "can", "could", "may", "might", "must", "this",
        "that", "these", "those", "i", "you", "he", "she", "it", "we", "they",
        "them", "their", "our", "your", "his", "her", "its", "as", "such",
        "than", "too", "very", "just", "also", "etc", "per", "via", "within",
        "across", "including", "include", "includes", "ability", "able",
        "experience", "experiences", "work", "working", "job", "role", "team",
        "teams", "company", "candidate", "candidates", "looking", "seeking",
        "required", "requirements", "responsibilities", "responsible",
        "preferred", "plus", "strong", "good", "great", "excellent", "year",
        "years", "knowledge", "skill", "skills", "using", "use", "used",
        "well", "new", "help", "ensure", "support", "provide", "provides",
        "you'll", "we're", "etc.", "join", "build", "building", "develop",
        "developing", "developer", "engineer", "senior", "junior", "lead",
    }
)
