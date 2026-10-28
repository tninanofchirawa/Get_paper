"""
harvester/models.py - Unified academic paper representation and normalizers.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

import re
import html
import datetime
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any


def sanitize_title(raw_title: str) -> str:
    """Removes HTML tags, LaTeX macros, curly braces, and redundant whitespace from paper titles."""
    if not raw_title:
        return ""
    # Strip HTML tags
    t = re.sub(r"<[^>]+>", " ", str(raw_title))
    # Unescape HTML entities
    t = html.unescape(t)
    # Strip LaTeX formatting like \textbf{...}, \textit{...}, \text{...}
    t = re.sub(r"\\[a-zA-Z]+\{([^}]*)\}", r"\1", t)
    # Replace math expressions or clean braces
    t = re.sub(r"[{}\\]", "", t)
    # Normalize excessive whitespace
    return re.sub(r"\s+", " ", t).strip()


def sanitize_doi(raw_doi: Any) -> str:
    """Extracts a canonical lowercase DOI string (e.g. '10.1109/2.53') from a raw string or URL."""
    if not raw_doi:
        return ""
    s = str(raw_doi).strip()
    if s.lower() in ("nan", "none", "null", "undefined", "-", "not verified"):
        return ""
    # Strip URL prefixes
    s = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", s, flags=re.IGNORECASE)
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


@dataclass
class Paper:
    """Core academic paper representation harvested across providers and enriched with verification flags."""
    title: str = ""
    authors: str = ""
    year: str = ""
    publication_type: str = "Journal Article"
    venue: str = ""
    doi: str = ""
    url: str = ""
    pdf_link: str = ""
    source: str = ""
    abstract: str = ""
    access_type: str = ""
    issn_list: List[str] = field(default_factory=list)

    # Verification & Indexing Statuses
    scopus_indexed: Optional[bool] = None
    wos_indexed: Optional[bool] = None
    ieee_indexed: Optional[bool] = None
    open_access: Optional[bool] = None
    verification_source: str = ""

    # Analytical / Materials Database metadata
    material_id: str = ""
    main_problem: str = ""
    main_application: str = ""
    importance: str = "High"
    learning_level: str = "Intermediate"
    primary_category_id: str = "GEN.01"
    primary_category_name: str = "Foundations"
    secondary_cats: List[Tuple[str, str]] = field(default_factory=list)
    research_status: str = "Identified"
    reading_status: str = "Not Started"
    relevance_score: int = 10
    notes: str = ""
    date_added: str = ""

    # Internal normalized fields
    clean_title: str = field(init=False, repr=False, default="")
    clean_doi: str = field(init=False, repr=False, default="")

    def __post_init__(self):
        self.title = sanitize_title(self.title)
        self.clean_title = clean_matching_title(self.title)
        self.clean_doi = sanitize_doi(self.doi)

        if self.clean_doi and not self.doi:
            self.doi = self.clean_doi

        if not self.url and self.clean_doi:
            self.url = f"https://doi.org/{self.clean_doi}"

        if self.year:
            self.year = clean_year(self.year)

        if not self.date_added:
            self.date_added = datetime.date.today().isoformat()

        if self.abstract:
            self.abstract = re.sub(r"\s+", " ", html.unescape(self.abstract)).strip()

    def to_verified_row(self) -> Dict[str, Any]:
        """Maps record to standard Row 11+ output columns."""
        def bool_to_yn(val: Optional[bool]) -> str:
            if val is True:
                return "Y"
            if val is False:
                return "N"
            return "Pending"

        return {
            # Section 5 exact requested columns
            "Title": self.title,
            "Authors": self.authors,
            "Publication Year": self.year,
            "Journal/Source": self.venue,
            "DOI": self.clean_doi or self.doi,
            "URL": self.url,
            "Scopus Indexed (Y/N)": bool_to_yn(self.scopus_indexed),
            "WoS Indexed (Y/N)": bool_to_yn(self.wos_indexed),
            "IEEE Indexed (Y/N)": bool_to_yn(self.ieee_indexed),
            "OpenAccess (Y/N)": bool_to_yn(self.open_access),
            "Verification Source": self.verification_source or "OpenAlex Fallback",

            # Materials Database detailed columns
            "Material ID": self.material_id,
            "Publication Type": self.publication_type,
            "PDF Link": self.pdf_link,
            "Source": self.source,
            "Abstract / Short Summary": self.abstract,
            "Main Research Problem": self.main_problem,
            "Main Application": self.main_application,
            "Importance": self.importance,
            "Learning Level": self.learning_level,
            "Primary Category ID": self.primary_category_id,
            "Primary Category Name": self.primary_category_name,
            "Research Status": self.research_status,
            "Reading Status": self.reading_status,
            "Relevance Score": self.relevance_score,
            "Notes": self.notes,
            "Date Added": self.date_added,
        }
