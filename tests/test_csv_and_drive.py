"""
tests/test_csv_and_drive.py - Unit tests for:
1. Standardized Two-Tier UTF-8 CSV builder (Rows 1-15 Metadata Block, Row 16 Headers at Col B across 32 analytical fields, Row 17+ Records at Col B).
2. RFC 4180 escaping and UTF-8 with BOM encoding.
3. Google Drive API v3 sync & storage quota 403 error prevention (Method 1 User OAuth 2.0, Method 2 Shared Drive, supportsAllDrives=True).
4. Email service delivery reliability across SMTP with non-crashing exception handling.
"""

import os
import csv
import json
import unittest
from unittest.mock import MagicMock, patch

from config import cfg
from csv_builder import StandardizedCsvBuilder
from drive_sync import GoogleDriveClient
from email_service import EmailDispatcher
from harvester.models import Paper
from analyzer import PaperAnalyzer


class TestStandardizedCsvBuilder(unittest.TestCase):
    def setUp(self):
        self.test_output = os.path.join(cfg.OUTPUT_DIR, "test_export.csv")
        if os.path.exists(self.test_output):
            os.remove(self.test_output)

    def tearDown(self):
        if os.path.exists(self.test_output):
            try:
                os.remove(self.test_output)
            except Exception:
                pass

    def test_csv_32_analytical_fields(self):
        """Validates all 32 analytical columns are present in exact schema order."""
        fields = StandardizedCsvBuilder.ANALYTICAL_FIELDS_32
        self.assertEqual(len(fields), 32)
        self.assertEqual(fields[0], "Material ID")
        self.assertEqual(fields[1], "Title")
        self.assertEqual(fields[2], "Authors")
        self.assertEqual(fields[3], "Year")
        self.assertEqual(fields[4], "DOI")
        self.assertEqual(fields[5], "Venue")
        self.assertEqual(fields[6], "Publication Type")
        self.assertEqual(fields[7], "URL")
        self.assertEqual(fields[8], "PDF Link")
        self.assertEqual(fields[9], "Source")
        self.assertEqual(fields[10], "Index Status")
        self.assertEqual(fields[11], "Scopus Indexed")
        self.assertEqual(fields[12], "WoS Indexed")
        self.assertEqual(fields[13], "IEEE Indexed")
        self.assertEqual(fields[14], "Open Access Status")
        self.assertEqual(fields[15], "Citation Count")
        self.assertEqual(fields[16], "Verified Sources")
        self.assertEqual(fields[17], "Abstract")
        self.assertEqual(fields[31], "Date Added")

    def test_two_tier_layout_and_escaping(self):
        """
        Verifies the complete two-tier template:
        - Tier 1: Rows 1-15 Metadata Block (Cols B & C Primary Metrics, Col D Blank, Cols E & F Secondary Analytics, Row 15 buffer).
        - Tier 2: Row 16 Headers starting at Col B across 32 analytical fields.
        - Row 17+: Paper record starting at Col B.
        - UTF-8 with BOM & RFC 4180 quote escaping.
        """
        paper = Paper(
            title='Complex "Fuzzy" Logic & α-Cuts, Part 1',
            authors="Zadeh, L. A.; Bellman, R. E.",
            year="2024",
            venue="IEEE Transactions on Fuzzy Systems, Vol. 32",
            doi="10.1109/TFUZZ.2024.123456",
            url="https://doi.org/10.1109/TFUZZ.2024.123456",
            pdf_link="https://ieeexplore.ieee.org/stamp/123456.pdf",
            source="Crossref",
            scopus_indexed=True,
            wos_indexed=True,
            ieee_indexed=True,
            open_access=False,
            citation_count=42,
            verified_sources=["Scopus", "Web of Science", "Crossref"],
            abstract='Line 1 with "quotes" and, commas.\nLine 2 with math: θ = 0.5 & α-cuts.'
        )
        analyzed = PaperAnalyzer.analyze_paper(paper, query="fuzzy logic", material_idx=1)

        run_config = {
            "run_name": "Test_TwoTier_Run_01",
            "topics": ["Fuzzy Logic Systems"],
            "harvest_quota": 100,
            "only_indexed": True,
            "duration": "12.4s",
            "location": "Home",
            "target_repos": ["Scopus", "OpenAlex", "Crossref"]
        }
        metrics = {"raw_scraped": 10, "duplicates_removed": 1, "verified_retained": 1}

        csv_path = StandardizedCsvBuilder.generate_csv(
            papers=[analyzed],
            run_config=run_config,
            metrics=metrics,
            output_filepath=self.test_output
        )

        self.assertTrue(os.path.exists(csv_path))

        # Read back with standard csv.reader
        with open(csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            rows = list(reader)

        # Total rows: 15 (Metadata) + 1 (Row 16 Headers) + 1 (Row 17 Data) = 17 rows
        self.assertEqual(len(rows), 17)

        # Check Row 1 (Index 0): Col B = Query String, Col D = Blank, Col E = Scopus/WoS Verified Count
        row_1 = rows[0]
        self.assertEqual(row_1[0], "")  # Col A blank
        self.assertEqual(row_1[1], "Query String")
        self.assertEqual(row_1[2], "Fuzzy Logic Systems")
        self.assertEqual(row_1[3], "")  # Col D blank separator
        self.assertEqual(row_1[4], "Scopus/WoS Verified Count")
        self.assertEqual(row_1[5], "1")

        # Check Row 15 (Index 14): Blank buffer row before tabular data
        row_15 = rows[14]
        self.assertTrue(all(val == "" for val in row_15))

        # Check Row 16 (Index 15): Data column headers strictly on Row 16, beginning at Column B
        row_16 = rows[15]
        self.assertEqual(row_16[0], "")  # Col A blank
        self.assertEqual(row_16[1:], StandardizedCsvBuilder.TABLE_HEADERS)
        self.assertEqual(len(row_16[1:]), len(StandardizedCsvBuilder.TABLE_HEADERS))
        self.assertIn("Verified_Via", row_16[1:])

        # Check Row 17 (Index 16): Paper record strictly on Row 17, beginning at Column B
        row_17 = rows[16]
        self.assertEqual(row_17[0], "")  # Col A blank
        self.assertEqual(row_17[1], "M-0001")
        self.assertEqual(row_17[2], 'Complex "Fuzzy" Logic & α-Cuts, Part 1')
        self.assertEqual(row_17[3], "Zadeh, L. A.; Bellman, R. E.")
        self.assertEqual(row_17[4], "2024")
        self.assertEqual(row_17[5], "10.1109/tfuzz.2024.123456")
        self.assertEqual(row_17[6], "IEEE Transactions on Fuzzy Systems, Vol. 32")
        self.assertEqual(row_17[11], "Indexed (Scopus, WoS, IEEE)")  # Index Status
        self.assertEqual(row_17[12], "Y")  # Scopus
        self.assertEqual(row_17[13], "Y")  # WoS
        self.assertEqual(row_17[14], "Y")  # IEEE
        self.assertEqual(row_17[15], "N")  # Open Access
        self.assertEqual(row_17[16], "42") # Citation Count

        # Verified Sources column validation
        v_sources = json.loads(row_17[17])
        self.assertEqual(v_sources, ["Scopus", "Web of Science", "Crossref"])

        # Verified_Via column validation
        self.assertEqual(row_17[18], "Unverified")

        # Multiline abstract integrity & quotes escaping
        self.assertIn('Line 1 with "quotes" and, commas.', row_17[19])
        self.assertIn("Line 2 with math: θ = 0.5 & α-cuts.", row_17[19])


class TestGoogleDriveStorageAndQuota(unittest.TestCase):
    def test_service_account_root_prevention(self):
        """Verifies that service account uploads without a target folder_id are safely intercepted before hitting 403 quota error."""
        client = GoogleDriveClient(folder_id="")
        client.service = MagicMock()
        client.auth_mode = "service_account"
        client.service_account_email = "test-service-acct@test.iam.gserviceaccount.com"

        temp_file = os.path.join(cfg.OUTPUT_DIR, "temp_quota_test.csv")
        os.makedirs(cfg.OUTPUT_DIR, exist_ok=True)
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write("A,B\n1,2\n")

        try:
            file_id = client.upload_file(temp_file)
            self.assertIsNone(file_id)
            client.service.files().create.assert_not_called()
        finally:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception:
                    pass

    def test_supports_all_drives_flag_and_parents_folder(self):
        """Verifies supportsAllDrives=True and parents=[folder_id] are strictly enforced in Drive API v3 create."""
        client = GoogleDriveClient(folder_id="shared_folder_12345")
        mock_files = MagicMock()
        mock_create = MagicMock()
        mock_create.execute.return_value = {
            "id": "drive_file_999",
            "name": "Run_Test.csv",
            "webViewLink": "https://drive.google.com/file/d/drive_file_999/view"
        }
        mock_files.create.return_value = mock_create
        client.service = MagicMock()
        client.service.files.return_value = mock_files
        client.auth_mode = "service_account"

        temp_file = os.path.join(cfg.OUTPUT_DIR, "temp_shared_drive_test.csv")
        os.makedirs(cfg.OUTPUT_DIR, exist_ok=True)
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write("Material ID,Title\nM-0001,Test\n")

        try:
            with patch("drive_sync.MediaFileUpload"):
                file_id = client.upload_file(temp_file, custom_filename="Run_Test.csv")
                self.assertEqual(file_id, "drive_file_999")
                self.assertEqual(client.get_last_link(), "https://drive.google.com/file/d/drive_file_999/view")

                mock_files.create.assert_called_once()
                call_kwargs = mock_files.create.call_args[1]
                self.assertTrue(call_kwargs.get("supportsAllDrives"))
                body = call_kwargs.get("body")
                self.assertEqual(body.get("parents"), ["shared_folder_12345"])
                self.assertEqual(body.get("name"), "Run_Test.csv")
        finally:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception:
                    pass

    def test_user_oauth_mode_preflight_success(self):
        """Verifies that User OAuth 2.0 mode passes pre-flight checks and uploads under user account ownership."""
        client = GoogleDriveClient(folder_id="")
        mock_files = MagicMock()
        mock_create = MagicMock()
        mock_create.execute.return_value = {
            "id": "oauth_file_111",
            "name": "OAuth_Run.csv",
            "webViewLink": "https://drive.google.com/file/d/oauth_file_111/view"
        }
        mock_files.create.return_value = mock_create
        client.service = MagicMock()
        client.service.files.return_value = mock_files
        client.auth_mode = "oauth_user"

        temp_file = os.path.join(cfg.OUTPUT_DIR, "temp_oauth_test.csv")
        os.makedirs(cfg.OUTPUT_DIR, exist_ok=True)
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write("A,B\n1,2\n")

        try:
            with patch("drive_sync.MediaFileUpload"):
                file_id = client.upload_file(temp_file, custom_filename="OAuth_Run.csv")
                self.assertEqual(file_id, "oauth_file_111")
                mock_files.create.assert_called_once()
        finally:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception:
                    pass


class TestEmailReliabilityAndMetrics(unittest.TestCase):
    def test_non_crashing_email_exception_handling(self):
        """Verifies email failures do not crash execution or throw unhandled exceptions."""
        dispatcher = EmailDispatcher(provider="smtp")
        with patch("smtplib.SMTP", side_effect=ConnectionRefusedError("Connection refused")):
            success = dispatcher._send_smtp(
                subject="Test Failure",
                html_body="<p>Test</p>",
                plain_body="Test",
                to_email="nobody@example.com",
                from_header="Test <test@example.com>"
            )
            self.assertFalse(success)

            safe_result = dispatcher.send("Test Safe", "<p>Safe</p>")
            self.assertFalse(safe_result)

    def test_run_completion_report_metrics_and_drive_link(self):
        """Verifies report builder formats metrics, excluded non-indexed papers, and Drive links."""
        dispatcher = EmailDispatcher(provider="console")
        run_config = {
            "run_name": "Run_Consistent_Identifier_42",
            "location": "Home",
            "topics": ["Fuzzy Networks"]
        }
        metrics = {
            "raw_scraped": 200,
            "duplicates_removed": 20,
            "verified_retained": 150,
            "excluded_non_indexed": 30,
            "duration_seconds": 45
        }
        drive_link = "https://drive.google.com/file/d/test_file_id/view"

        temp_csv = os.path.join(cfg.OUTPUT_DIR, "temp_report_test.csv")
        os.makedirs(cfg.OUTPUT_DIR, exist_ok=True)
        with open(temp_csv, "w", encoding="utf-8") as f:
            f.write("A,B\n1,2\n")

        try:
            with patch.object(dispatcher, "send", return_value=True) as mock_send:
                res = dispatcher.send_run_completion_report(
                    run_config=run_config,
                    metrics=metrics,
                    csv_path=temp_csv,
                    drive_link=drive_link
                )
                self.assertTrue(res)
                mock_send.assert_called_once()
                call_args = mock_send.call_args[0]
                subject = call_args[0]
                html_body = call_args[1]
                plain_body = call_args[2]

                # Assert dynamic naming consistency
                self.assertIn("Run_Consistent_Identifier_42", subject)
                self.assertIn("Run_Consistent_Identifier_42", plain_body)
                self.assertIn("Run_Consistent_Identifier_42", html_body)

                # Assert metrics inclusion
                self.assertIn("200", plain_body)  # raw_scraped
                self.assertIn("150", plain_body)  # verified_retained
                self.assertIn("30", plain_body)   # excluded_non_indexed
                self.assertIn(drive_link, plain_body)
                self.assertIn(drive_link, html_body)
        finally:
            if os.path.exists(temp_csv):
                os.remove(temp_csv)


if __name__ == "__main__":
    unittest.main()
