"""
batch_runner.py - Resilient batch file processor fixing the 3-of-4 files processed bug.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

import os
import sys
import logging
import traceback
from pathlib import Path
from typing import List, Dict, Any, Optional

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import pandas as pd

from config import cfg
from database import db
from harvester.models import Paper, sanitize_doi
from verifier.dual_branch import DualBranchVerifier
from analyzer import PaperAnalyzer
from excel_builder import StandardizedExcelBuilder
from csv_builder import StandardizedCsvBuilder
from cache_cleaner import purge_stale_cache

logger = logging.getLogger("BatchRunner")


class ResilientBatchRunner:
    """
    Deterministically processes file queues with strict error boundaries and SQLite run-state tracking.
    Eliminates the '3 out of 4 Files Processed' bug by preventing silent task drops.
    Lifecycles: QUEUED -> RUNNING -> COMPLETED or FAILED.
    """

    def __init__(self, verifier: Optional[DualBranchVerifier] = None):
        self.verifier = verifier or DualBranchVerifier()

    @staticmethod
    def get_deterministic_file_queue(input_dir: str = cfg.INPUT_DIR) -> List[Path]:
        """
        Discovers all CSV files in deterministic alphabetical order using pathlib.Path.
        Filters out hidden files and temporary lock files.
        """
        p = Path(input_dir)
        if not p.exists():
            return []
        csv_files = [
            f for f in sorted(p.glob("*.csv"))
            if not f.name.startswith((".", "~$")) and f.is_file()
        ]
        return csv_files

    @staticmethod
    def detect_identifier_column(df: pd.DataFrame) -> str:
        """Heuristically detects DOI / URL / Title columns."""
        lower_cols = {str(c).lower().strip(): c for c in df.columns}
        for cand in ["clean_doi", "doi", "url", "pdf link", "title"]:
            if cand in lower_cols:
                return lower_cols[cand]
        return df.columns[0] if len(df.columns) > 0 else ""

    def process_single_file(
        self,
        file_path: Path,
        run_id: str,
        run_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Processes a single input file wrapped in strict try/except/finally error boundaries.
        Never drops execution silently: logs QUEUED -> RUNNING -> COMPLETED / FAILED in SQLite.
        """
        file_str = str(file_path.resolve())
        db.update_file_status(file_str, "RUNNING")
        logger.info(f"[Batch Worker] Ingesting '{file_path.name}'...")
        print(f"\n📂 [Batch Ingest] Starting file: '{file_path.name}'")

        try:
            # 1. Read CSV safely
            df = pd.read_csv(file_path, dtype=str, keep_default_na=False, encoding_errors="replace")
            if df.empty:
                logger.warning(f"[Batch Worker] '{file_path.name}' contains 0 data rows.")
                db.update_file_status(file_str, "COMPLETED", processed_count=0, verified_count=0)
                return {"status": "EMPTY", "file": file_path.name, "rows": 0, "verified": 0}

            # 2. Parse into Paper models
            papers: List[Paper] = []
            id_col = self.detect_identifier_column(df)
            print(f"  🔍 Detected column: '{id_col}' | Candidate records: {len(df)}")

            for idx, row in df.iterrows():
                row_dict = row.to_dict()
                title = str(row_dict.get("Title", "")).strip()
                doi = sanitize_doi(row_dict.get("DOI") or row_dict.get("Clean_DOI") or row_dict.get(id_col, ""))
                authors = str(row_dict.get("Authors", "")).strip()
                year = str(row_dict.get("Year") or row_dict.get("Publication Year", "")).strip()
                venue = str(row_dict.get("Journal / Conference") or row_dict.get("Journal/Source", "")).strip()
                pub_type = str(row_dict.get("Publication Type", "Journal Article")).strip()
                url = str(row_dict.get("URL", "")).strip()
                pdf = str(row_dict.get("PDF Link", "")).strip()
                source = str(row_dict.get("Source", "Batch File")).strip()
                abstract = str(row_dict.get("Abstract / Short Summary", "")).strip()

                if not title and not doi:
                    continue

                papers.append(Paper(
                    title=title,
                    authors=authors,
                    year=year,
                    publication_type=pub_type,
                    venue=venue,
                    doi=doi,
                    url=url,
                    pdf_link=pdf,
                    source=source,
                    abstract=abstract
                ))

            # 3. Verify batch records (supporting strict Scopus/WoS filtering if requested)
            only_indexed = run_config.get("only_indexed", False)
            verified_papers = self.verifier.verify_batch(papers, only_indexed=only_indexed)
            excluded_count = getattr(self.verifier, "last_excluded_count", 0)

            # 4. Enrich taxonomy and analysis categories
            topic_label = file_path.stem.replace("_materials_database", "").replace("_", " ").title()
            analyzed_papers = []
            for idx, p in enumerate(verified_papers, 1):
                ap = PaperAnalyzer.analyze_paper(p, query=topic_label, material_idx=idx)
                analyzed_papers.append(ap)

            # 5. Output standardized UTF-8 CSV
            out_name = f"{file_path.stem}_verified.csv"
            out_path = os.path.join(cfg.OUTPUT_DIR, out_name)

            metrics = {
                "raw_scraped": len(papers),
                "duplicates_removed": len(df) - len(papers),
                "verified_retained": len(analyzed_papers),
                "excluded_non_indexed": excluded_count
            }

            StandardizedCsvBuilder.generate_csv(
                papers=analyzed_papers,
                run_config={**run_config, "main_topic": topic_label},
                metrics=metrics,
                output_filepath=out_path
            )

            # 6. Log success to SQLite
            db.update_file_status(
                file_str,
                "COMPLETED",
                processed_count=len(papers),
                verified_count=len(analyzed_papers)
            )
            print(f"  ✅ [OK] Completed '{file_path.name}' -> {len(analyzed_papers)} verified records.")
            return {"status": "SUCCESS", "file": file_path.name, "rows": len(papers), "verified": len(analyzed_papers)}

        except Exception as e:
            err_msg = f"{type(e).__name__}: {str(e)}"
            logger.error(f"[Batch Worker ERROR] Failed processing '{file_path.name}': {err_msg}")
            print(f"  ❌ [FAIL] Exception in '{file_path.name}': {err_msg}")
            db.update_file_status(file_str, "FAILED", error_message=err_msg)
            return {"status": "FAILED", "file": file_path.name, "error": err_msg}

    def run_all(self, run_id: str, run_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes complete deterministic queue ingestion across all CSV files in input/.
        Guarantees every file is logged, processed, and tracked without freezing.
        """
        file_queue = self.get_deterministic_file_queue()
        total_files = len(file_queue)

        print("\n" + "=" * 76)
        print(f"🚀 RESILIENT DETERMINISTIC BATCH RUNNER - {total_files} FILES DISCOVERED")
        print("=" * 76)

        # Enqueue all tasks deterministically in SQLite with 'QUEUED' status
        file_paths_str = [str(f.resolve()) for f in file_queue]
        db.enqueue_files(run_id, file_paths_str)

        results = []
        for idx, file_path in enumerate(file_queue, 1):
            print(f"\n[{idx}/{total_files}] Processing: {file_path.name}")
            res = self.process_single_file(file_path, run_id, run_config)
            results.append(res)

        summary = db.get_queue_summary(run_id)
        print("\n" + "=" * 76)
        print("📊 BATCH EXECUTION SUMMARY:")
        print(f"• Total Files Enqueued : {summary['total_files']}")
        print(f"• Successfully Completed: {summary['completed']}")
        print(f"• Failed Tasks         : {summary['failed']}")
        print(f"• Pending/Dropped      : {summary['pending']}")
        print("=" * 76 + "\n")

        # Immediately purge stale cache files following completed batch run
        purge_stale_cache()

        return summary
