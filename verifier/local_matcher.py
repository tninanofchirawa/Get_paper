"""
verifier/local_matcher.py - Offline O(1) set matching against Scopus/WoS journal master lists.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

import os
import logging
from typing import Optional, Set, List
import pandas as pd

from config import cfg

logger = logging.getLogger("LocalMatcher")


class LocalDBMatcher:
    """
    Loads official Scopus and Web of Science (WoS) title lists into fast in-memory
    hash sets for instant O(1) offline index verification via ISSN intersection.
    """

    def __init__(
        self,
        scopus_file_path: Optional[str] = None,
        wos_file_path: Optional[str] = None
    ):
        scopus_path = scopus_file_path or cfg.SCOPUS_LOCAL_DB_PATH
        wos_path = wos_file_path or cfg.WOS_LOCAL_DB_PATH

        self.scopus_issns: Set[str] = self._load_issn_set(scopus_path, "Scopus")
        self.wos_issns: Set[str] = self._load_issn_set(wos_path, "Web of Science")

    @staticmethod
    def clean_issn(raw_issn: str) -> str:
        """Strips hyphens, spaces, and normalizes to uppercase 8-char string."""
        if not raw_issn:
            return ""
        return str(raw_issn).replace("-", "").strip().upper()

    def _load_issn_set(self, file_path: Optional[str], database_name: str) -> Set[str]:
        """Loads all print and electronic ISSNs from an Excel or CSV file."""
        issn_set: Set[str] = set()
        if not file_path or not os.path.exists(file_path):
            logger.debug(f"[{database_name} Local DB] File not found or not specified: '{file_path}'. Offline set empty.")
            return issn_set

        try:
            if file_path.lower().endswith(".csv"):
                df = pd.read_csv(file_path, low_memory=False, dtype=str)
            else:
                df = pd.read_excel(file_path, dtype=str)

            for col in df.columns:
                if "issn" in str(col).lower():
                    for item in df[col].dropna():
                        cleaned = self.clean_issn(item)
                        if len(cleaned) == 8:
                            issn_set.add(cleaned)

            logger.info(f"[{database_name} Local DB] Loaded {len(issn_set)} active ISSN entries from '{file_path}'.")
        except Exception as e:
            logger.warning(f"[{database_name} Local DB] Could not load '{file_path}': {e}")

        return issn_set

    def is_scopus_issn(self, issn_list: List[str]) -> Optional[bool]:
        """Returns True if any paper ISSN matches the local Scopus database. Returns None if DB not loaded."""
        if not self.scopus_issns:
            return None
        return any(self.clean_issn(issn) in self.scopus_issns for issn in issn_list if issn)

    def is_wos_issn(self, issn_list: List[str]) -> Optional[bool]:
        """Returns True if any paper ISSN matches the local Web of Science database. Returns None if DB not loaded."""
        if not self.wos_issns:
            return None
        return any(self.clean_issn(issn) in self.wos_issns for issn in issn_list if issn)


# Alias LocalMatcher to LocalDBMatcher for convenience
LocalMatcher = LocalDBMatcher
