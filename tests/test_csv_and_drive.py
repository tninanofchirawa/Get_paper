"""
tests/test_csv_and_drive.py - Unit tests for:
1. Standardized UTF-8 CSV builder (schema, field order, escaping, Verified Sources column).
2. Dynamic run identifier mapping across CSV, Drive title, and Email subject/body.
3. Google Drive API v3 sync & storage quota 403 error prevention (Option A, B, C, supportsAllDrives=True).
4. Email service delivery reliability across SMTP/Mailgun/SendGrid with non-crashing exception handling.
"""

import os
import csv
import json
import unittest
from unittest.mock import MagicMock, patch

from csv_builder import StandardizedCsvBuilder
from drive_sync import GoogleDriveClient
from email_service import EmailDispatcher
from harvester.models import Paper
from analyzer import PaperAnalyzer


class TestStandardizedCsvBuilder(unittest.TestCase):
    def setUp(self):
        self.test_output = "output/test_export.csv"
        if os.path.exists(self.test_output):
            os.remove(self.test_output)

    def tearDown(self):
        if os.path.exists(self.test_output):
            try:
                os.remove(self.test_output)
            except Exception:
                pass

    def test_csv_table_headers_and_field_order(self):
        """Validates all 37 columns are present in exact schema order."""
        headers = StandardizedCsvBuilder.TABLE_HEADERS
        self.assertEqual(len(headers), 37)
        self.assertEqual(headers[0], "Material ID")
        self.assertEqual(headers[1], "Title")
        self.assertEqual(headers[2], "Authors")
        self.assertEqual(headers[3], "Publication Year")
        self.assertEqual(headers[4], "Journal/Source")
        self.assertEqual(headers[5], "Publication Type")
        self.assertEqual(headers[6], "DOI")
        self.assertEqual(headers[7], "URL")
        self.assertEqual(headers[8], "PDF Link")
        self.assertEqual(headers[9], "Source")
        self.assertEqual(headers[10], "Scopus Indexed (Y/N)")
        self.assertEqual(headers[11], "WoS Indexed (Y/N)")
        self.assertEqual(headers[12], "IEEE Indexed (Y/N)")
        self.assertEqual(headers[13], "OpenAccess (Y/N)")
        self.assertEqual(headers[14], "Verified Sources")
        self.assertEqual(headers[15], "Abstract / Short Summary")
        self.assertEqual(headers[36], "Date Added")

    def test_escaping_and_utf8_generation(self):
        """Verifies multiline text, commas, quotation marks, and UTF-8 characters are escaped cleanly."""
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
            verified_sources=["Scopus", "Web of Science", "Crossref"],
            abstract='Line 1 with "quotes" and, commas.\nLine 2 with math: θ = 0.5 & α-cuts.'
        )
        analyzed = PaperAnalyzer.analyze_paper(paper, query="fuzzy logic", material_idx=1)

        run_config = {"run_name": "Test_Escaping_Run_01"}
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

        self.assertEqual(len(rows), 2)  # Header + 1 Data row
        header_row = rows[0]
        data_row = rows[1]

        self.assertEqual(header_row, StandardizedCsvBuilder.TABLE_HEADERS)
        self.assertEqual(data_row[0], "M-0001")
        self.assertEqual(data_row[1], 'Complex "Fuzzy" Logic & α-Cuts, Part 1')
        self.assertEqual(data_row[6], "10.1109/tfuzz.2024.123456")
        self.assertEqual(data_row[10], "Y")
        self.assertEqual(data_row[11], "Y")
        self.assertEqual(data_row[12], "Y")
        self.assertEqual(data_row[13], "N")

        # Verified Sources column validation
        v_sources = json.loads(data_row[14])
        self.assertEqual(v_sources, ["Scopus", "Web of Science", "Crossref"])

        # Multiline abstract integrity
        self.assertIn('Line 1 with "quotes" and, commas.', data_row[15])
        self.assertIn("Line 2 with math: θ = 0.5 & α-cuts.", data_row[15])


class TestGoogleDriveStorageAndQuota(unittest.TestCase):
    def test_service_account_root_prevention(self):
        """Verifies that service account uploads without a target folder_id are safely intercepted before hitting 403 quota error."""
        client = GoogleDriveClient(folder_id="")
        client.service = MagicMock()
        client.auth_mode = "service_account"
        client.service_account_email = "test-service-acct@test.iam.gserviceaccount.com"

        # Create temporary file
        temp_file = "output/temp_quota_test.csv"
        os.makedirs("output", exist_ok=True)
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write("A,B\n1,2\n")

        try:
            # Must return None and log prevention message
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

        temp_file = "output/temp_shared_drive_test.csv"
        os.makedirs("output", exist_ok=True)
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write("Material ID,Title\nM-0001,Test\n")

        try:
            with patch("drive_sync.MediaFileUpload"):
                file_id = client.upload_file(temp_file, custom_filename="Run_Test.csv")
                self.assertEqual(file_id, "drive_file_999")
                self.assertEqual(client.get_last_link(), "https://drive.google.com/file/d/drive_file_999/view")

                # Check files().create kwargs
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


class TestEmailReliabilityAndMetrics(unittest.TestCase):
    def test_non_crashing_email_exception_handling(self):
        """Verifies email failures do not crash execution or throw unhandled exceptions."""
        dispatcher = EmailDispatcher(provider="smtp")
        # Force an invalid SMTP host to trigger network failure
        with patch("smtplib.SMTP", side_effect=ConnectionRefusedError("Connection refused")):
            success = dispatcher._send_smtp(
                subject="Test Failure",
                html_body="<p>Test</p>",
                plain_body="Test",
                to_email="nobody@example.com",
                from_header="Test <test@example.com>"
            )
            self.assertFalse(success)

            # High-level send method must also catch exceptions safely
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

        temp_csv = "output/temp_report_test.csv"
        os.makedirs("output", exist_ok=True)
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
