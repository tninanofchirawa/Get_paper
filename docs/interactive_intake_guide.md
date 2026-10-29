# 🧭 Interactive Intake & Questionnaire Deep Dive

## Unified Academic Paper Harvester & Verifier — Comprehensive Intake Guide

This document provides an exhaustive, question-by-question breakdown of every interactive prompt, CLI argument, and email configuration tag utilized across the pipeline. For each question, the underlying engineering rationale, default behavior, downstream algorithmic branching, and multiple-choice options are detailed.

---

## 📑 Index of Intake Questions

| # | CLI / Terminal Prompt | Email Configuration Tag | Core Functionality |
|---|-----------------------|-------------------------|--------------------|
| 1 | `[1/15] Run Name` | `[NAME_OF_RUN]` | Dynamic identifier mapping across CSV, Drive, and Email |
| 2 | `[2/15] Type of Run` | `[RUN_TYPE]` | Operational mode (Automated, Spontaneous, Batch) |
| 3 | `[3/15] Execution Location` | `[LOCATION]` | Network topology and institutional token strategy |
| 4 | `[4/15] Batch Execution` | `[BATCH_RUN]` | Directory-wide ingest across all files in `input/` |
| 5 | `[5/15] Batch Details` | `[BATCH_DETAILS]` | Selective batch subsetting or start position |
| 6 | `[6/15] Output Mode` | `[OUTPUT_MODE]` | Workbook creation vs. schema appending |
| 7 | `[7/15] Target Sheet / File` | `[TARGET_SHEET]` | Destination spreadsheet or file path |
| 8 | `[8/15] Main Topic / Topics` | `[TOPIC_COUNT]`, `[TOPIC_1..5]` | Semantic search seeds across academic aggregators |
| 9 | `[9/15] Subtopics per Topic` | `[T1_SUBTOPICS..T5_SUBTOPICS]` | Disambiguation keywords & domain qualifiers |
| 10 | `[10/15] Target Quota` | `[PAPERS_PER_TOPIC]` | Volume target per topic (100, 250, 500 cap) |
| 11 | `[11/15] Year Range` | `[YEAR_RANGE]` | Chronological publication boundaries |
| 12 | `[12/15] Document Filter` | `[DOC_TYPE]` | Publication venue type (Journals, Conferences, Preprints) |
| 13 | `[13/15] Institutional Token` | `[INST_TOKEN]` | Elsevier Scopus, Clarivate WoS, and IEEE Xplore auth |
| 14 | `[14/15] Only Indexed Filter` | `[ONLY_INDEXED]` | Strict Scopus / Web of Science retention filter |
| 15 | `[15/15] Quota Strictness` | `[QUOTA_STRICTNESS]` | Active accumulator pagination vs. fast initial cap |

---

## 🔍 Detailed Question-by-Question Deep Dive

### Question 1: Run Name / Query Identifier
- **Prompt:** `[1/15] Run Name (Press Enter for auto timestamp):`
- **Email Tag:** `[NAME_OF_RUN]: Run_YYYYMMDD_01`
- **CLI Flag:** `--run-name <identifier>`
- **Underlying Rationale:**
  A uniform run identifier is vital for data lineage and traceability. The pipeline processes hundreds of citations per execution; assigning a deterministic name prevents accidental file overwrites, enables longitudinal study tracking, and synchronizes the local filesystem with Google Drive and notification subjects.
- **Default / Recommended Behavior:**
  Pressing Enter or omitting the tag defaults to `Run_YYYYMMDD_HHMMSS` (e.g., `Run_20261029_083000`). If triggered via scheduled email, it defaults to `Run_YYYYMMDD_01`.
- **Follow-Up Handling & Downstream Branching:**
  The sanitized string is used dynamically to:
  1. Generate the local CSV export: `output/{run_name}.csv`.
  2. Set the uploaded file title in Google Drive v3: `custom_filename="{run_name}.csv"`.
  3. Format the email subject line: `✅ [Harvest Complete] {run_name} — {verified_count} Papers Verified & Synced!`.
  4. Anchor the primary key in SQLite audit database: `db.log_run_start(run_id, run_name, run_config)`.

---

### Question 2: Type of Run
- **Prompt:** `[2/15] Type of Run: [1] Automated Scheduled  [2] Spontaneous Manual  [3] Batch File Run`
- **Email Tag:** `[RUN_TYPE]: Automated | Manual | Batch`
- **Underlying Rationale:**
  Controls logging verbosity, execution lifecycle, and whether interactive terminal prompts should wait or auto-resolve defaults.
- **Selectable Choices:**
  1. `[1] Automated Scheduled`: Headless execution triggered by cron or the 3-tier IST reminder daemon (`scheduler.py`). Suppresses all interactive `input()` calls.
  2. `[2] Spontaneous Manual (Default)`: Single-topic ad-hoc exploration entered directly in terminal or triggered via CLI `--query`.
  3. `[3] Batch File Run`: Ingests pre-existing candidate datasets from `input/` folder in alphabetical order.
- **Downstream Branching:**
  Selecting choice `3` bypasses Questions 8–15 and routes execution to [`ResilientBatchRunner`](file:///c:/Users/rohan/Documents/##%20Code/5)%20October%20-%202026/The_Paper_Getter/batch_runner.py).

---

### Question 3: Execution Location
- **Prompt:** `[3/15] Execution Location: [1] HITS Campus  [2] Home  [3] Online Remote VPS`
- **Email Tag:** `[LOCATION]: HITS Campus | Home | Online VPS`
- **Underlying Rationale:**
  Academic APIs (specifically Elsevier Scopus and Clarivate Web of Science) enforce IP-range whitelisting. Knowing the network context allows the verifier to predict whether IP-based institutional access will succeed or whether secure tokens/fallbacks are mandatory.
- **Selectable Choices Breakdown:**
  - `[1] HITS Campus`: Connected to university intranet/WiFi. Enables IP-based Elsevier Scopus validation without requiring explicit `ELSEVIER_INST_TOKEN`.
  - `[2] Home (Default)`: Off-campus residential broadband. Requires institutional token or routes to Open Access fallback (Branch 2).
  - `[3] Online Remote VPS`: Cloud servers (e.g. AWS, DigitalOcean, Railway). Institutional IP authentication will fail; requires explicit tokens or fallback to OpenAlex/Crossref.

---

### Question 4 & 5: Batch Execution & Batch Details
- **Prompt:** `[4/15] Batch Execution across all input files? (y/N):`
- **Email Tag:** `[BATCH_RUN]: Yes | No` / `[BATCH_DETAILS]: <file_name>`
- **CLI Flag:** `--all`, `--batch`
- **Underlying Rationale:**
  Permits processing bulk literature dumps (e.g. Scopus export CSVs, PubMed extracts).
- **Default Behavior:**
  Default is `No`. If `Yes`, `ResilientBatchRunner` scans `input/*.csv` alphabetically, skips 0-byte or corrupted files, sanitizes column headers, and exports `{stem}_verified.csv`.

---

### Question 6 & 7: Output Mode & Target Sheet
- **Prompt:** Interactive workbook output preferences.
- **Email Tag:** `[OUTPUT_MODE]: Create New | Append to Existing` / `[TARGET_SHEET]: <name>`
- **Underlying Rationale:**
  Controls whether a fresh standalone CSV/workbook is created per run or appended into an existing materials master spreadsheet.
- **Default Behavior:**
  `Create New` is the standard mode. Emits an RFC 4180 UTF-8 CSV with all 37 standardized columns.

---

### Question 8: Research Topics & Topic Count
- **Prompt:** `[8 & 9/15] Enter Main Topic (e.g. Fuzzy Logic & Neural Networks):`
- **Email Tag:** `[TOPIC_COUNT]: 2` followed by `[TOPIC_1]..[TOPIC_5]`
- **CLI Flag:** `--query "<topic>"`
- **Underlying Rationale:**
  Serves as the root lexical query for the asynchronous accumulator harvester.
- **Boundary Limits:**
  - Maximum topics per run: **5** (hard-capped to protect API rate caps).
- **Default Behavior:**
  `fuzzy logic` if left blank in terminal.

---

### Question 9: Subtopics per Topic
- **Prompt:** `Enter up to 5 subtopics (comma separated, or press Enter):`
- **Email Tag:** `[T1_SUBTOPICS]: Subtopic 1, Subtopic 2, Subtopic 3, Subtopic 4, Subtopic 5`
- **Underlying Rationale:**
  Broad queries like "Machine Learning" return millions of noisy hits. Specifying subtopics (e.g., "T-Norms, ANFIS, Neuro-Fuzzy") narrows search vectors across OpenAlex and Semantic Scholar, enhancing precision and relevance scoring.
- **Boundary Limits:**
  - Maximum subtopics per topic: **5**. Excess subtopics trigger an error response notice.

---

### Question 10: Target Quota
- **Prompt:** `[10/15] Target Quota per topic [100, 250, 500] (default: 250):`
- **Email Tag:** `[PAPERS_PER_TOPIC]: 100 | 250 | 500`
- **CLI Flag:** `--quota <int>`
- **Underlying Rationale:**
  Defines the exact number of verified, unique papers to retain before concluding the active accumulator pagination loop.
- **Presets & Trade-Offs:**
  - `100`: High speed (~15–30 seconds), ideal for quick literature scans.
  - `250 (Default)`: Balanced speed and coverage (~45–90 seconds), recommended for systematic reviews.
  - `500 (Hard Cap)`: Exhaustive coverage (~2–4 minutes), maximum allowable before triggering vendor rate throttles.

---

### Question 11: Year Range
- **Prompt:** `[11/15] Year Range (e.g. 2021-2026 or Enter for All Years):`
- **Email Tag:** `[YEAR_RANGE]: 2021-2026 | All Years`
- **Underlying Rationale:**
  Restricts literature searches to recent state-of-the-art work or admits historical foundational papers.
- **Downstream Branching:**
  Transformed into provider-specific query parameters:
  - OpenAlex: `filter=publication_year:2021-2026`
  - Crossref: `filter=from-pub-date:2021-01-01,until-pub-date:2026-12-31`
  - Semantic Scholar: `year=2021-2026`

---

### Question 12: Document Filter
- **Prompt:** `[12/15] Document Filter: [1] All  [2] Journal Articles  [3] Conferences  [4] Preprints`
- **Email Tag:** `[DOC_TYPE]: Journal Articles Only | Conference Proceedings | Preprints | All`
- **Options Breakdown:**
  1. `[1] All`: Retains journal articles, conference papers, preprints, book chapters.
  2. `[2] Journal Articles Only (Default)`: Filters strictly for peer-reviewed journal articles.
  3. `[3] Conference Proceedings`: Focuses on IEEE, ACM, Springer LNCS proceedings.
  4. `[4] Preprints`: Focuses on arXiv, bioRxiv, and OpenAlex preprints.

---

### Question 13: Institutional Token Enablement
- **Prompt:** `[13/15] Enable Institutional Token (Scopus/WoS/IEEE)? (y/N, default: Y if configured):`
- **Email Tag:** `[INST_TOKEN]: True | False`
- **Underlying Rationale:**
  Directs the verification engine to attempt Branch 1 (Elsevier Scopus API, Clarivate WoS API, IEEE Xplore) or immediately use Branch 2 (OpenAlex, Crossref, local hash matching).
- **Default Behavior:**
  `True` if `ELSEVIER_API_KEY` and `ELSEVIER_INST_TOKEN` are populated in `.env`; otherwise `False`.

---

### Question 14: Strict Indexing Filter (`--only-indexed`)
- **Prompt:** `[14/15] Filter for indexed-only papers (Scopus / Web of Science)? [y/N]:`
- **Email Tag:** `[ONLY_INDEXED]: True | False`
- **CLI Flag:** `--only-indexed`
- **Underlying Rationale:**
  For thesis chapters, tenure evaluations, and grant reporting, papers must strictly appear in Scopus or Web of Science indices.
- **Downstream Branching:**
  - `True (Strict)`: Any harvested paper not confirmed by Scopus or Web of Science is dropped. The number of dropped non-indexed papers is tallied and logged as `excluded_non_indexed`.
  - `False (Broad Default)`: Retains papers confirmed by OpenAlex, Crossref, Semantic Scholar, or arXiv even if Scopus/WoS records are absent.

---

### Question 15: Quota Strictness
- **Prompt:** `[15/15] Quota Strictness: [1] Strict (Paginate until quota met)  [2] Fast/Capped`
- **Email Tag:** `[QUOTA_STRICTNESS]: Strict | Fast-Capped`
- **Underlying Rationale:**
  Controls the persistence of the accumulator pagination loop.
- **Options Breakdown:**
  - `Strict (Default)`: The loop keeps requesting new pages across providers until `len(unique_papers) >= target_quota` or all provider APIs return exhausted cursors. Eliminates the 83/87 item freezing bug.
  - `Fast-Capped`: Halts after the initial harvest round regardless of whether the quota was fully met. Used for low-latency testing.
