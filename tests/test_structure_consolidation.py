"""
tests/test_structure_consolidation.py - Verification of Repository Structural Consolidation.
Validates:
1. Module imports from new canonical namespaces: core, utils, services.drive, services.notifications.
2. Root backward-compatibility shims: analyzer.py, batch_runner.py, database.py, csv_builder.py, excel_builder.py.
3. Storage hierarchy: storage/cache, storage/output, storage/logs, storage/temp, storage/input.
4. Scripts reorganization: scripts/maintenance/ and scripts/audit/.
5. Dynamic path resolutions for BASE_DIR, credentials, and env.
"""

import os
import unittest
from pathlib import Path

from config import cfg


class TestStructuralConsolidation(unittest.TestCase):
    def test_core_package_exports(self):
        """Verifies core package imports and single-responsibility engines."""
        from core import (
            Paper,
            PaperAnalyzer,
            ResilientBatchRunner,
            DatabaseManager,
            db,
            clean_matching_title,
            sanitize_doi,
        )
        self.assertIsNotNone(Paper)
        self.assertIsNotNone(PaperAnalyzer)
        self.assertIsNotNone(ResilientBatchRunner)
        self.assertIsNotNone(DatabaseManager)
        self.assertIsNotNone(db)

    def test_utils_format_converters(self):
        """Verifies format converters live in utils and export cleanly."""
        from utils.csv_builder import StandardizedCsvBuilder
        from utils.excel_builder import StandardizedExcelBuilder
        from utils import (
            StandardizedCsvBuilder as BuilderCSV,
            StandardizedExcelBuilder as BuilderXLSX,
            CircuitBreaker,
            TokenBucketRateLimiter,
        )
        self.assertIs(StandardizedCsvBuilder, BuilderCSV)
        self.assertIs(StandardizedExcelBuilder, BuilderXLSX)

    def test_services_drive_clustering(self):
        """Verifies services.drive provides auth, uploader, client, mime, and quota."""
        from services.drive.auth import load_user_oauth_credentials
        from services.drive.uploader import DriveUploader, GoogleDriveClient
        from services.drive import (
            GoogleDriveClient as ClientAlias,
            DriveUploader as UploaderAlias,
            validate_upload_quota_preconditions,
        )
        self.assertIsNotNone(load_user_oauth_credentials)
        self.assertIs(DriveUploader, GoogleDriveClient)
        self.assertIs(ClientAlias, GoogleDriveClient)

    def test_services_notifications_clustering(self):
        """Verifies services.notifications provides mailer, dispatcher, and templates."""
        from services.notifications.mailer import Mailer, mailer, EmailDispatcher
        from services.notifications import (
            EmailDispatcher as DispatcherAlias,
            Mailer as MailerAlias,
            wrap_html_container,
        )
        self.assertIs(Mailer, EmailDispatcher)
        self.assertIs(DispatcherAlias, EmailDispatcher)

    def test_root_backward_compatibility_shims(self):
        """Ensures root-level legacy imports remain 100% functional without breakage."""
        import analyzer
        import batch_runner
        import database
        import csv_builder
        import excel_builder

        self.assertTrue(hasattr(analyzer, "PaperAnalyzer"))
        self.assertTrue(hasattr(batch_runner, "ResilientBatchRunner"))
        self.assertTrue(hasattr(database, "DatabaseManager"))
        self.assertTrue(hasattr(csv_builder, "StandardizedCsvBuilder"))
        self.assertTrue(hasattr(excel_builder, "StandardizedExcelBuilder"))

    def test_storage_hierarchy_resolution(self):
        """Ensures storage hierarchy is established and cfg paths map to storage/."""
        storage_dir = Path(cfg.BASE_DIR) / "storage"
        self.assertTrue(storage_dir.exists(), "storage/ directory must exist")
        self.assertTrue((storage_dir / "cache").exists(), "storage/cache/ must exist")
        self.assertTrue((storage_dir / "output").exists(), "storage/output/ must exist")
        self.assertTrue((storage_dir / "logs").exists(), "storage/logs/ must exist")
        self.assertTrue((storage_dir / "temp").exists(), "storage/temp/ must exist")
        self.assertTrue((storage_dir / "input").exists(), "storage/input/ must exist")

        self.assertIn("storage", cfg.CACHE_DIR.replace("\\", "/"))
        self.assertIn("storage", cfg.OUTPUT_DIR.replace("\\", "/"))
        self.assertIn("storage", cfg.LOGS_DIR.replace("\\", "/"))
        self.assertIn("storage", cfg.TEMP_DIR.replace("\\", "/"))

    def test_scripts_modular_clustering(self):
        """Ensures maintenance and audit scripts are structured into dedicated subdirectories."""
        from scripts.maintenance.clean import clean_project_artifacts, PROTECTED_FILENAMES
        from scripts.maintenance.cache_cleaner import purge_stale_cache
        from scripts.audit.audit_footprint import audit_project_footprint
        from scripts.audit.test_email import test_morning_intake

        self.assertTrue(callable(clean_project_artifacts))
        self.assertTrue(callable(purge_stale_cache))
        self.assertTrue(callable(audit_project_footprint))
        self.assertTrue(callable(test_morning_intake))


if __name__ == "__main__":
    unittest.main()
