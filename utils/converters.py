"""
utils/converters.py - Data sanitization, title cleaning, DOI parsing, and format converters.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

import re
import html
from typing import Any, Optional


def sanitize_title(title: Optional[str]) -> str:
    """
    Strips XML/HTML formatting tags (<b>, <i>, <inf>), LaTeX commands (\\textbf{}, \\textit{}),
    escapes entities, and collapses redundant internal whitespace.
    """
    if not title:
        return ""
    text = html.unescape(str(title))
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Remove standard LaTeX styling commands e.g. \textbf{...}, \textit{...}
    text = re.sub(r"\\[a-zA-Z]+{([^}]*)}", r"\1", text)
    # Remove lone backslashes and LaTeX markers
    text = re.sub(r"\\[a-zA-Z]+", "", text)
    # Clean control characters and multiple whitespaces
    text = re.sub(r"[\r\n\t]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def sanitize_doi(raw_doi: Optional[str]) -> str:
    """
    Extracts canonical lowercase DOI matching format '10.xxxx/...',
    stripping URL prefixes, leading/trailing punctuation, and resolvers.
    """
    if not raw_doi:
        return ""
    s = str(raw_doi).strip()
    if s.lower() in ("not verified", "none", "null", "n/a", "-"):
        return ""
    # Strip URL prefixes
    s = re.sub(r"^https?://(dx\.)?doi\.org/", "", s, flags=re.IGNORECASE)
    s = re.sub(r"^doi:\s*", "", s, flags=re.IGNORECASE)

    # Match standard DOI prefix 10.xxxx/...
    match = re.search(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", s)
    if match:
        cleaned = match.group(0).lower().rstrip(".")
        return re.sub(r"[;,.)]+$", "", cleaned)
    if s.startswith("10.") and "/" in s:
        return s.lower()
    return ""


def clean_matching_title(title: str) -> str:
    """Produces an alphanumeric-only lowercase title for fuzzy similarity comparison."""
    sanitized = sanitize_title(title)
    alphanumeric = re.sub(r"[^a-zA-Z0-9\s]", " ", sanitized).lower()
    return re.sub(r"\s+", " ", alphanumeric).strip()


def clean_year(raw_year: Any) -> str:
    """Extracts a 4-digit publication year (e.g., 2024)."""
    if not raw_year:
        return ""
    m = re.search(r"\b(19\d{2}|20\d{2})\b", str(raw_year))
    return m.group(1) if m else ""
