"""Prompt Injection Scanner.

Sanitizes user questions before they enter the LLM prompt.
Detects and scores injection attempts using pattern matching.
"""

from __future__ import annotations

import re
import unicodedata

import structlog

logger = structlog.get_logger(__name__)


# Known override / jailbreak phrases
_OVERRIDE_PATTERNS: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE) for p in [
        r"ignore\s+(previous|all|above)\s+(instructions?|rules?|constraints?)",
        r"forget\s+(all\s+)?(instructions?|rules?|constraints?|context)",
        r"you\s+are\s+now\s+\w+",
        r"pretend\s+(to\s+be|you\s+are)",
        r"act\s+as\s+(if\s+you\s+are|a\s+)",
        r"disregard\s+(all\s+)?(rules?|instructions?)",
        r"new\s+system\s+prompt",
        r"override\s+(mode|rules?|instructions?)",
        r"(reveal|show|print)\s+.*(password|secret|key|token|schema)",
        r"jailbreak",
        r"DAN\s+mode",
    ]
]

# SQL keywords that are suspicious in natural language questions
_SQL_FRAGMENT_PATTERNS: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE) for p in [
        r"\bUNION\s+SELECT\b",
        r"\bINSERT\s+INTO\b",
        r"\bDELETE\s+FROM\b",
        r"\bDROP\s+TABLE\b",
        r"\bALTER\s+TABLE\b",
        r"\bCREATE\s+(TABLE|DATABASE|USER)\b",
        r"\bEXEC(\s+|\()",
        r"\bsp_executesql\b",
        r"--\s*$",          # SQL comment at end of line
        r"/\*.*\*/",        # Block comments
        r"\bxp_cmdshell\b",
        r"\bEXECUTE\s+IMMEDIATE\b",
    ]
]

# Encoding bypass markers (pre-normalization)
_ENCODING_PATTERNS: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE) for p in [
        r"\\x[0-9a-fA-F]{2}",     # Hex escape
        r"\\u[0-9a-fA-F]{4}",     # Unicode escape
        r"%[0-9a-fA-F]{2}",       # URL encoding
    ]
]


def _normalize_encodings(text: str) -> str:
    """Decode escape sequences and normalize to UTF-8."""
    # URL decode
    import urllib.parse
    try:
        text = urllib.parse.unquote(text)
    except Exception:
        pass
    # Unicode normalization (NFKC)
    text = unicodedata.normalize("NFKC", text)
    return text


def _score_overrides(text: str) -> float:
    """Score override/jailbreak attempt (0.0–1.0)."""
    matches = sum(1 for p in _OVERRIDE_PATTERNS if p.search(text))
    return min(1.0, matches * 0.4)


def _score_sql_fragments(text: str) -> float:
    """Score raw SQL embedded in the question (0.0–1.0)."""
    matches = sum(1 for p in _SQL_FRAGMENT_PATTERNS if p.search(text))
    return min(1.0, matches * 0.35)


def _score_encoding_bypass(raw_text: str) -> float:
    """Score encoding bypass attempts (0.0–1.0)."""
    matches = sum(1 for p in _ENCODING_PATTERNS if p.search(raw_text))
    return min(1.0, matches * 0.5)


class ScanResult:
    def __init__(self, sanitized_text: str, risk_score: float, flags: list[str]):
        self.sanitized_text = sanitized_text
        self.risk_score = risk_score
        self.flags = flags

    @property
    def is_injection(self) -> bool:
        return self.risk_score >= 0.7

    @property
    def is_suspicious(self) -> bool:
        return 0.3 <= self.risk_score < 0.7


def scan(question: str, injection_threshold: float = 0.7) -> ScanResult:
    """Scan a user question for prompt injection attempts.

    Returns a ScanResult with:
    - sanitized_text: cleaned version of the question
    - risk_score: 0.0 (clean) to 1.0 (definite injection)
    - flags: list of detected issue categories
    """
    flags: list[str] = []

    # 1. Detect encoding bypass before normalization
    encoding_score = _score_encoding_bypass(question)
    if encoding_score > 0:
        flags.append("ENCODING_BYPASS")

    # 2. Normalize
    normalized = _normalize_encodings(question)

    # 3. Override detection
    override_score = _score_overrides(normalized)
    if override_score > 0:
        flags.append("OVERRIDE_ATTEMPT")

    # 4. SQL fragment detection
    sql_score = _score_sql_fragments(normalized)
    if sql_score > 0:
        flags.append("SQL_FRAGMENT")

    # 5. Aggregate score
    risk_score = min(1.0, override_score + sql_score + encoding_score)

    # 6. Sanitize: strip known injection phrases from text
    sanitized = normalized
    for pattern in _OVERRIDE_PATTERNS:
        sanitized = pattern.sub("[REDACTED]", sanitized)

    log = logger.bind(risk_score=risk_score, flags=flags)
    if risk_score >= injection_threshold:
        log.warning("Prompt injection detected", question_preview=question[:80])
    elif risk_score >= 0.3:
        log.info("Suspicious question flagged", question_preview=question[:80])

    return ScanResult(sanitized_text=sanitized, risk_score=risk_score, flags=flags)
