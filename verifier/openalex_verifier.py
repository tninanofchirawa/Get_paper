"""
verifier/openalex_verifier.py - OpenAlex CC0 registry fallback and ISSN inspector.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

import logging
from typing import Optional, Dict, Any, List

import requests

from config import cfg
from verifier.local_db import LocalDBMatcher

logger = logging.getLogger("OpenAlexVerifier")


class OpenAlexVerifier:
    """Fallback verifier leveraging OpenAlex CC0 open registry and ISSN extraction."""

    def __init__(self, local_db: Optional[LocalDBMatcher] = None):
        self.local_db = local_db or LocalDBMatcher()
        self.session = requests.Session()
        self.session.headers.update(cfg.get_http_headers("openalex"))

    def check_work(self, doi: str) -> Optional[Dict[str, Any]]:
        """
        Inspects OpenAlex work record for Scopus indexing, ISSNs, Open Access URL, and host venue.
        """
        clean_doi = doi.strip()
        if not clean_doi:
            return None

        url = f"https://api.openalex.org/works/https://doi.org/{clean_doi}"
        try:
            resp = self.session.get(url, timeout=12)
            if resp.status_code == 200:
                work = resp.json()
                primary_loc = work.get("primary_location") or {}
                source = primary_loc.get("source") or {}

                # Check is_in_scopus across primary location and alternate locations
                is_scopus = source.get("is_in_scopus") is True
                if not is_scopus:
                    for loc in work.get("locations", []):
                        loc_src = (loc or {}).get("source") or {}
                        if loc_src.get("is_in_scopus") is True:
                            is_scopus = True
                            source = loc_src
                            break

                journal = source.get("display_name") or ""
                publisher = source.get("host_organization_name") or ""
                issns = source.get("issn") or []

                # Local Scopus/WoS ISSN check
                scopus_local = self.local_db.is_scopus_issn(issns)
                wos_local = self.local_db.is_wos_issn(issns)

                if scopus_local is True:
                    is_scopus = True

                oa_obj = work.get("open_access") or {}
                is_oa = oa_obj.get("is_oa") is True
                oa_url = oa_obj.get("oa_url") or primary_loc.get("pdf_url") or ""

                return {
                    "is_scopus_indexed": is_scopus,
                    "is_wos_indexed": wos_local,
                    "journal": journal,
                    "publisher": publisher,
                    "issns": issns,
                    "is_oa": is_oa,
                    "oa_url": oa_url,
                    "found": True
                }
            return None
        except Exception as e:
            logger.debug(f"[OpenAlexVerifier] Error querying DOI {clean_doi}: {e}")
            return None
