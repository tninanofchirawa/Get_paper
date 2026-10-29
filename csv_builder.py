"""
csv_builder.py - Production-grade UTF-8 CSV builder for academic paper harvesting.
Generates standardized, RFC 4180-compliant CSV files retaining exact column schemas,
proper escaping for multiline abstracts/quotes, and dynamic run identifier mappings.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

import os
import csv
import json
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from config import cfg
from harvester.models import Paper


class StandardizedCsvBuilder:
    """
    Constructs UTF-8 CSV files strictly adhering to Section 5 table schema:
    - 37 Standardized Columns in exact field order.
    - RFC 4180 quoting and escaping rules for commas, newlines, and quotes.
    - UTF-8 with BOM (utf-8-sig) ensuring seamless rendering across Microsoft Excel, Google Sheets, and pandas.
    - Consolidated 'Verified Sources' column with structured JSON list representation.
    """

    TABLE_HEADERS = [
        "Material ID",
        "Title",
        "Authors",
        "Publication Year",
        "Journal/Source",
        "Publication Type",
        "DOI",
        "URL",
        "PDF Link",
        "Source",
        "Scopus Indexed (Y/N)",
        "WoS Indexed (Y/N)",
        "IEEE Indexed (Y/N)",
        "OpenAccess (Y/N)",
        "Verified Sources",
        "Abstract / Short Summary",
        "Main Research Problem",
        "Main Application",
        "Importance",
        "Learning Level",
        "Primary Category ID",
        "Primary Category Name",
        "Secondary Category 1 ID",
        "Secondary Category 1 Name",
        "Secondary Category 2 ID",
        "Secondary Category 2 Name",
        "Secondary Category 3 ID",
        "Secondary Category 3 Name",
        "Secondary Category 4 ID",
        "Secondary Category 4 Name",
        "Secondary Category 5 ID",
        "Secondary Category 5 Name",
        "Research Status",
        "Reading Status",
        "Relevance Score",
        "Notes",
        "Date Added"
    ]

    @staticmethod
    def _bool_to_yn(val: Optional[bool]) -> str:
        return "Y" if val is True else ("N" if val is False else "N")

    @classmethod
    def paper_to_row(cls, p: Paper) -> List[Any]:
        """Maps a Paper dataclass into a standardized list of values matching TABLE_HEADERS."""
        sec_cats = list(p.secondary_cats) if p.secondary_cats else []
        while len(sec_cats) < 5:
            sec_cats.append(("", ""))

        # Consolidated Verified Sources JSON string
        sources = list(p.verified_sources) if p.verified_sources else []
        if not sources and p.verification_source:
            sources = [s.strip() for s in p.verification_source.split(",") if s.strip()]
        verified_sources_str = json.dumps(sources)

        return [
            p.material_id,
            p.title,
            p.authors,
            p.year,
            p.venue,
            p.publication_type,
            p.clean_doi or p.doi,
            p.url,
            p.pdf_link,
            p.source,
            cls._bool_to_yn(p.scopus_indexed),
            cls._bool_to_yn(p.wos_indexed),
            cls._bool_to_yn(p.ieee_indexed),
            cls._bool_to_yn(p.open_access),
            verified_sources_str,
            p.abstract,
            p.main_problem,
            p.main_application,
            p.importance,
            p.learning_level,
            p.primary_category_id,
            p.primary_category_name,
            sec_cats[0][0], sec_cats[0][1],
            sec_cats[1][0], sec_cats[1][1],
            sec_cats[2][0], sec_cats[2][1],
            sec_cats[3][0], sec_cats[3][1],
            sec_cats[4][0], sec_cats[4][1],
            p.research_status,
            p.reading_status,
            p.relevance_score,
            p.notes,
            p.date_added
        ]

    @classmethod
    def generate_csv(
        cls,
        papers: List[Paper],
        run_config: Dict[str, Any],
        metrics: Optional[Dict[str, Any]] = None,
        output_filepath: Optional[str] = None,
        append_mode: bool = False,
        include_metadata_header: bool = False
    ) -> str:
        """
        Creates or appends to a standardized UTF-8 CSV file.
        Returns the absolute filepath to the generated CSV.
        """
        if not output_filepath:
            run_name = run_config.get("run_name") or f"Run_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
            output_filepath = os.path.join(cfg.OUTPUT_DIR, f"{run_name}.csv")
        elif output_filepath.lower().endswith(".xlsx"):
            output_filepath = output_filepath[:-5] + ".csv"

        target_path = Path(output_filepath).resolve()
        target_path.parent.mkdir(parents=True, exist_ok=True)

        file_exists = target_path.exists() and target_path.stat().st_size > 0
        mode = "a" if (append_mode and file_exists) else "w"

        # UTF-8 with BOM ensures Excel opens UTF-8 characters without encoding defects
        with open(target_path, mode=mode, encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")

            # Write optional metadata comment lines when starting a new file
            if include_metadata_header and not (append_mode and file_exists):
                now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                run_name = run_config.get("run_name", target_path.stem)
                f.write(f"# Run Name: {run_name}\n")
                f.write(f"# Run Type: {run_config.get('run_type', 'Manual')}\n")
                f.write(f"# Timestamp: {run_config.get('timestamp', now_str)}\n")
                f.write(f"# Location: {run_config.get('location', 'Home')}\n")
                if metrics:
                    f.write(f"# Raw Scraped: {metrics.get('raw_scraped', len(papers))}\n")
                    f.write(f"# Duplicates Removed: {metrics.get('duplicates_removed', 0)}\n")
                    f.write(f"# Verified Retained: {metrics.get('verified_retained', len(papers))}\n")
                    f.write(f"# Excluded Non-Indexed: {metrics.get('excluded_non_indexed', 0)}\n")

            # Write header row if new file or overwriting
            if not (append_mode and file_exists):
                writer.writerow(cls.TABLE_HEADERS)

            # Write data rows
            for p in papers:
                writer.writerow(cls.paper_to_row(p))

        print(f"[CsvBuilder] Successfully exported {len(papers)} verified papers to: {target_path}")
        return str(target_path)


# Backward-compatibility alias
generate_standardized_csv = StandardizedCsvBuilder.generate_csv
