"""
excel_builder.py - Production-grade Excel workbook builder.
Renders standardized Rows 1-10 run parameters header and Row 11+ verified paper database.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

import os
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from config import cfg
from harvester.models import Paper


class StandardizedExcelBuilder:
    """
    Constructs Excel workbooks adhering strictly to Section 5:
    - Rows 1 to 10: Metadata and run parameters (Columns A, B, C spacer, D, E).
    - Row 11: Production Table Header row.
    - Rows 12+: Verified paper records with full schema.
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
        "Verification Source",
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

    # Styling palettes
    HEADER_FILL = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    META_KEY_FILL = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    META_VAL_FILL = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
    HEADER_FONT = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    META_KEY_FONT = Font(name="Calibri", size=10, bold=True, color="1F4E78")
    REGULAR_FONT = Font(name="Calibri", size=10)
    BOLD_FONT = Font(name="Calibri", size=10, bold=True)
    THIN_BORDER = Border(
        left=Side(style='thin', color='D9D9D9'),
        right=Side(style='thin', color='D9D9D9'),
        top=Side(style='thin', color='D9D9D9'),
        bottom=Side(style='thin', color='D9D9D9')
    )

    @classmethod
    def write_metadata_block(
        cls,
        ws: openpyxl.worksheet.worksheet.Worksheet,
        run_config: Dict[str, Any],
        metrics: Dict[str, int]
    ):
        """Populates Rows 1 to 10 strictly according to Section 5 specification."""
        topics_raw = run_config.get("topics") or run_config.get("main_topics") or []
        main_topic_str = topics_raw[0] if topics_raw else run_config.get("main_topic", "Fuzzy Systems & Soft Computing")
        subtopics = run_config.get("subtopics", [])

        # Column A & B: Primary Metadata Label and Value
        meta_left = [
            ("Main Topic", main_topic_str),
            ("Subtopic 1", subtopics[0] if len(subtopics) > 0 else ""),
            ("Subtopic 2", subtopics[1] if len(subtopics) > 1 else ""),
            ("Subtopic 3", subtopics[2] if len(subtopics) > 2 else ""),
            ("Subtopic 4", subtopics[3] if len(subtopics) > 3 else ""),
            ("Subtopic 5", subtopics[4] if len(subtopics) > 4 else ""),
            ("Survey Question 1 (Harvest Quota & Year Range)", f"Target: {run_config.get('harvest_quota', cfg.DEFAULT_QUOTA)} | Years: {run_config.get('year_range', 'All Years')}"),
            ("Survey Question 2 (Document Classification Filter)", run_config.get("doc_filter", "All")),
            ("Survey Question 3 (Institutional Token & Target Repositories)", f"Inst Token: {'True' if run_config.get('inst_token_flag') else 'False'} | Repos: {', '.join(run_config.get('target_repos', ['Scopus', 'OpenAlex']))}"),
            ("Survey Question 4 (Quota Strictness & Execution Mode)", f"{run_config.get('quota_strictness', 'Strict')} | {run_config.get('output_mode', 'Create New Excel File')}")
        ]

        # Column D & E: Run Configuration Label and Value
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        batch_flag = "Yes" if run_config.get("is_batch") else "No"
        batch_pos = run_config.get("batch_details", "Single Topic Run")
        if isinstance(batch_pos, dict):
            batch_pos = batch_pos.get("position", "Single Run")

        meta_right = [
            ("Run Name", run_config.get("run_name", f"Run_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}")),
            ("Run Type", run_config.get("run_type", "Automated Scheduled")),
            ("Timestamp", run_config.get("timestamp", now_str)),
            ("Execution Location", run_config.get("location", "Home")),
            ("Batch Execution Flag", batch_flag),
            ("Batch Position / Name", str(batch_pos)),
            ("Verification Status", run_config.get("verification_status", "Dual-Branch Verified")),
            ("Target Quota", str(run_config.get("harvest_quota", cfg.DEFAULT_QUOTA))),
            ("Quota Reached / Verified Retained", str(metrics.get("verified_retained", 0))),
            ("Total Deduplicated / Raw Scraped", f"{metrics.get('duplicates_removed', 0)} dups removed ({metrics.get('raw_scraped', 0)} raw)")
        ]

        for row_idx in range(1, 11):
            # Col A (Key)
            k_left, v_left = meta_left[row_idx - 1]
            c_a = ws.cell(row=row_idx, column=1, value=k_left)
            c_a.font = cls.META_KEY_FONT
            c_a.fill = cls.META_KEY_FILL
            c_a.border = cls.THIN_BORDER
            c_a.alignment = Alignment(vertical="center")

            # Col B (Value)
            c_b = ws.cell(row=row_idx, column=2, value=v_left)
            c_b.font = cls.REGULAR_FONT
            c_b.fill = cls.META_VAL_FILL
            c_b.border = cls.THIN_BORDER
            c_b.alignment = Alignment(vertical="center")

            # Col C (Empty Spacer)
            c_c = ws.cell(row=row_idx, column=3, value="")
            c_c.border = Border()

            # Col D (Key)
            k_right, v_right = meta_right[row_idx - 1]
            c_d = ws.cell(row=row_idx, column=4, value=k_right)
            c_d.font = cls.META_KEY_FONT
            c_d.fill = cls.META_KEY_FILL
            c_d.border = cls.THIN_BORDER
            c_d.alignment = Alignment(vertical="center")

            # Col E (Value)
            c_e = ws.cell(row=row_idx, column=5, value=v_right)
            c_e.font = cls.REGULAR_FONT
            c_e.fill = cls.META_VAL_FILL
            c_e.border = cls.THIN_BORDER
            c_e.alignment = Alignment(vertical="center")

    @classmethod
    def write_table_header(cls, ws: openpyxl.worksheet.worksheet.Worksheet, row_num: int = 11):
        """Writes and formats Row 11 table headers."""
        for col_idx, header in enumerate(cls.TABLE_HEADERS, 1):
            cell = ws.cell(row=row_num, column=col_idx, value=header)
            cell.font = cls.HEADER_FONT
            cell.fill = cls.HEADER_FILL
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = cls.THIN_BORDER
        ws.row_dimensions[row_num].height = 28

    @classmethod
    def write_paper_rows(
        cls,
        ws: openpyxl.worksheet.worksheet.Worksheet,
        papers: List[Paper],
        start_row: int = 12
    ):
        """Writes verified paper records into worksheet starting from start_row."""
        current_row = start_row
        for p in papers:
            def yn(val: Optional[bool]) -> str:
                return "Y" if val is True else ("N" if val is False else "N")

            # Pad secondary categories to 5 slots
            sec_cats = list(p.secondary_cats) if p.secondary_cats else []
            while len(sec_cats) < 5:
                sec_cats.append(("", ""))

            row_data = [
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
                yn(p.scopus_indexed),
                yn(p.wos_indexed),
                yn(p.ieee_indexed),
                yn(p.open_access),
                p.verification_source,
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

            for col_idx, val in enumerate(row_data, 1):
                cell = ws.cell(row=current_row, column=col_idx, value=val)
                cell.font = cls.REGULAR_FONT
                cell.border = cls.THIN_BORDER
                # Center-align short metadata and indicators
                if col_idx in (1, 4, 6, 11, 12, 13, 14, 21, 23, 25, 27, 29, 31, 33, 34, 35, 37):
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                else:
                    cell.alignment = Alignment(vertical="center")

            current_row += 1

    @classmethod
    def auto_fit_columns(cls, ws: openpyxl.worksheet.worksheet.Worksheet):
        """Sets pleasant column widths based on headers and sample content."""
        col_width_defaults = {
            1: 15,   # Material ID
            2: 45,   # Title
            3: 30,   # Authors
            4: 16,   # Publication Year
            5: 35,   # Journal/Source
            6: 20,   # Publication Type
            7: 25,   # DOI
            8: 30,   # URL
            9: 30,   # PDF Link
            10: 16,  # Source
            11: 18,  # Scopus Indexed (Y/N)
            12: 18,  # WoS Indexed (Y/N)
            13: 18,  # IEEE Indexed (Y/N)
            14: 18,  # OpenAccess (Y/N)
            15: 25,  # Verification Source
            16: 40,  # Abstract
            17: 35,  # Problem
            18: 30,  # Application
        }
        for col_idx in range(1, len(cls.TABLE_HEADERS) + 1):
            letter = get_column_letter(col_idx)
            ws.column_dimensions[letter].width = col_width_defaults.get(col_idx, 22)
        # Spacer column C width
        ws.column_dimensions["C"].width = 5

    @classmethod
    def generate_workbook(
        cls,
        papers: List[Paper],
        run_config: Dict[str, Any],
        metrics: Dict[str, int],
        output_filepath: Optional[str] = None,
        sheet_name: str = "Verified Papers",
        append_mode: bool = False
    ) -> str:
        """
        Creates or appends to Excel file with full standardized specification.
        Returns the absolute filepath to the generated .xlsx workbook.
        """
        if not output_filepath:
            run_name = run_config.get("run_name") or f"Run_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
            output_filepath = os.path.join(cfg.OUTPUT_DIR, f"{run_name}.xlsx")

        os.makedirs(os.path.dirname(os.path.abspath(output_filepath)), exist_ok=True)

        if append_mode and os.path.exists(output_filepath):
            wb = openpyxl.load_workbook(output_filepath)
            if sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
                start_row = ws.max_row + 1
            else:
                ws = wb.create_sheet(title=sheet_name)
                cls.write_metadata_block(ws, run_config, metrics)
                cls.write_table_header(ws, row_num=11)
                start_row = 12
        else:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = sheet_name
            cls.write_metadata_block(ws, run_config, metrics)
            cls.write_table_header(ws, row_num=11)
            start_row = 12

        cls.write_paper_rows(ws, papers, start_row=start_row)
        cls.auto_fit_columns(ws)

        wb.save(output_filepath)
        print(f"[ExcelBuilder] Successfully exported {len(papers)} verified papers to: {output_filepath}")
        return str(Path(output_filepath).resolve())
