# 📘 Complete Handbook & Master Engineering Manual

## Unified Academic Paper Harvester, Verifier & 100% Gmail-Driven Pipeline 🎓

Welcome to the definitive engineering manual and user handbook for the **Unified Academic Paper Harvester & Verifier**. This manual provides an exhaustive walkthrough covering system architecture, interactive intake rationales, multiple-choice filter trade-offs, modular codebase organization, API concurrency compliance, automated nightly cache maintenance, and Google Drive cloud storage synchronization.

---

## 📑 Table of Contents

1. [🏗️ System Architecture & Data Flow](#1-️-system-architecture--data-flow)
2. [📁 Modular Directory Architecture](#2--modular-directory-architecture)
3. [❓ Question-by-Question Deep Dive (15-Point Intake)](#3--question-by-question-deep-dive-15-point-intake)
   - [Question 1: Run Name / Query Identifier](#question-1-run-name--query-identifier)
   - [Question 2: Type of Run](#question-2-type-of-run)
   - [Question 3: Execution Location](#question-3-execution-location)
   - [Question 4: Batch Execution](#question-4-batch-execution)
   - [Question 5: Batch Details](#question-5-batch-details)
   - [Question 6: Output Mode](#question-6-output-mode)
   - [Question 7: Target Sheet / File](#question-7-target-sheet--file)
   - [Question 8: Main Topic / Topic Count](#question-8-main-topic--topic-count)
   - [Question 9: Subtopics per Topic](#question-9-subtopics-per-topic)
   - [Question 10: Target Quota per Topic](#question-10-target-quota-per-topic)
   - [Question 11: Year Range](#question-11-year-range)
   - [Question 12: Document Type Filter](#question-12-document-type-filter)
   - [Question 13: Institutional Token Enablement](#question-13-institutional-token-enablement)
   - [Question 14: Strict Indexing Filter (--only-indexed)](#question-14-strict-indexing-filter---only-indexed)
   - [Question 15: Quota Strictness](#question-15-quota-strictness)
4. [🎯 Multiple-Choice Questions (MCQ) & Filters Breakdown](#4--multiple-choice-questions-mcq--filters-breakdown)
   - [Trade-Off Matrix: Speed vs. Coverage vs. Quota Impact](#trade-off-matrix-speed-vs-coverage-vs-quota-impact)
   - [Concrete Output Record Samples](#concrete-output-record-samples)
5. [⚡ API Configuration, Rate Limiting & Concurrency Compliance](#5--api-configuration-rate-limiting--concurrency-compliance)
   - [Semantic Scholar Strict 1 req/sec Architecture](#semantic-scholar-strict-1-reqsec-architecture)
   - [Mathematical Rate Limiting & Token Bucket Formulation](#mathematical-rate-limiting--token-bucket-formulation)
   - [HTTP 429 Exponential Backoff & Retry Mechanism](#http-429-exponential-backoff--retry-mechanism)
   - [Outbound Header Compliance & Token Pooling](#outbound-header-compliance--token-pooling)
   - [Multi-Provider Polite Pool & Rate Caps](#multi-provider-polite-pool--rate-caps)
6. [🌙 Automated Nightly Cache Invalidation & Maintenance](#6--automated-nightly-cache-invalidation--maintenance)
   - [Midnight 00:00 IST Automated Purge Routine](#midnight-0000-ist-automated-purge-routine)
   - [TTL Eviction Hierarchy](#ttl-eviction-hierarchy)
   - [Manual CLI Cache Flushing (--clear-cache)](#manual-cli-cache-flushing---clear-cache)
7. [☁️ Google Drive Cloud Storage & 403 Quota Resolution](#7-️-google-drive-cloud-storage--403-quota-resolution)
   - [Root Cause of the 403 Storage Quota Error](#root-cause-of-the-403-storage-quota-error)
   - [Option A: Google Shared Drive (Recommended)](#option-a-google-shared-drive-recommended)
   - [Option B: Personal Drive Shared Folder](#option-b-personal-drive-shared-folder)
   - [Option C: User-Level OAuth 2.0 Credentials](#option-c-user-level-oauth-20-credentials)
   - [Payload Size Tracking & Gzip Compression](#payload-size-tracking--gzip-compression)
8. [📋 Standardized 37-Column UTF-8 CSV Schema](#8--standardized-37-column-utf-8-csv-schema)
   - [Schema Definition & Field Specifications](#schema-definition--field-specifications)
   - [RFC 4180 Escaping Rules & Excel Compatibility](#rfc-4180-escaping-rules--excel-compatibility)
9. [🔬 Deduplication & Fuzzy Title Matching Algorithm](#9--deduplication--fuzzy-title-matching-algorithm)
   - [Two-Stage Deduplication Architecture](#two-stage-deduplication-architecture)
   - [Inverted Token Buckets & SequenceMatcher Math](#inverted-token-buckets--sequencematcher-math)
10. [🚀 Complete Beginner's Walkthrough](#10--complete-beginners-walkthrough)
   - [Step 1: Generating the Gmail 16-Character App Password](#step-1-generating-the-gmail-16-character-app-password)
   - [Step 2: Enabling IMAP in Gmail Settings](#step-2-enabling-imap-in-gmail-settings)
   - [Step 3: Setting Up Google Drive API & Service Account](#step-3-setting-up-google-drive-api--service-account)
   - [Step 4: Configuring the `.env` File](#step-4-configuring-the-env-file)
   - [Step 5: Testing Local Connectivity](#step-5-testing-local-connectivity)
11. [🛡️ Troubleshooting & Failure Recovery Matrix](#11-️-troubleshooting--failure-recovery-matrix)
   - [Scenario A: Elsevier Scopus 401/403 Authentication Failure](#scenario-a-elsevier-scopus-401403-authentication-failure)
   - [Scenario B: Semantic Scholar HTTP 429 Throttle Spike](#scenario-b-semantic-scholar-http-429-throttle-spike)
   - [Scenario C: Google Drive HttpError 403 Storage Quota Exceeded](#scenario-c-google-drive-httperror-403-storage-quota-exceeded)
   - [Scenario D: SMTP Authentication Rejection (Error 535)](#scenario-d-smtp-authentication-rejection-error-535)
   - [Scenario E: Inbound Email Formatting & Syntax Errors](#scenario-e-inbound-email-formatting--syntax-errors)
12. [⚙️ Production Deployment & Headless Daemon Operations](#12-️-production-deployment--headless-daemon-operations)
   - [Linux Systemd Service Setup](#linux-systemd-service-setup)
   - [Windows Task Scheduler & Background Daemon](#windows-task-scheduler--background-daemon)
   - [Crontab Configuration](#crontab-configuration)
13. [🛠️ CLI Reference & Command Index](#13-️-cli-reference--command-index)

---

## 1. 🏗️ System Architecture & Data Flow

The engine operates on a four-tier lifecycle: Scheduled User Intake, High-Speed Multi-Source Literature Harvesting with Deduplication, Dual-Branch Multi-Source Academic Verification, and Automated Standardization, Cloud Sync & Email Dispatch.

```mermaid
flowchart TD
    subgraph Intake["⏰ 1. Scheduled Intake Layer (100% Free Gmail)"]
        T1["07:30 AM IST: Morning Intake Questionnaire"] --> SMTP["SMTP Dispatch (Gmail App Password)"]
        T2["02:00 PM IST: Afternoon Follow-up"] --> SMTP
        T3["09:00 PM IST: Final Night Catch-up"] --> SMTP
        SMTP --> INB["Researcher Gmail Inbox"]
        INB -- "User Replies with [Harvester Run Config]" --> IMAP["IMAP Poller (Every 2 mins)"]
        IMAP --> PARSER["15-Tag Regex Parser & Validator"]
        PARSER -- "Validation Error" --> CORR["Send Corrective Email"]
        PARSER -- "Valid Config" --> PIPE["Async Harvesting Pipeline"]
    end

    subgraph Harv["⚡ 2. Asynchronous Accumulator Harvester"]
        PIPE --> ACC["Active Accumulator Loop (aiohttp)"]
        ACC --> OA["OpenAlex API (10 req/s)"]
        ACC --> CR["Crossref REST (50 req/s polite pool)"]
        ACC --> AR["arXiv Atom XML (3s polite delay)"]
        ACC --> SS["Semantic Scholar Graph API (1 req/s strict)"]
        OA & CR & AR & SS --> DEDUP["Deduplication Engine\n(Exact DOI + 90% Fuzzy Title Normalization)"]
        DEDUP -- "Paginates until verified >= Quota" --> QUEUE["Unique Candidate Papers Queue"]
    end

    subgraph Ver["🏛️ 3. Multi-Source Academic Verification"]
        QUEUE --> DUAL["DualBranchVerifier (ThreadPoolExecutor)"]
        DUAL --> CHK{"Institutional Token Available?"}
        CHK -- "Yes" --> B1["Branch 1: Commercial Institutional APIs"]
        B1 --> S1["Elsevier Scopus API (1.2s Pace)"]
        B1 --> S2["Clarivate Web of Science (WoS)"]
        B1 --> S3["IEEE Xplore REST API"]
        S1 & S2 & S3 -. "HTTP 401/403/429 (Circuit Trips)" .-> B2["Branch 2: Open Access & Offline Fallback"]
        CHK -- "No" --> B2
        B2 --> B2A["OpenAlex CC0 Registry"]
        B2 --> B2B["Crossref DOI Verification"]
        B2 --> B2C["arXiv Preprint Verification"]
        B2 --> B2D["Semantic Scholar Citation Verification"]
        B2 --> B2E["Local Scopus Source List (O(1) Hash)"]
        B2 --> B2F["Local WoS Master Journal List (O(1) Hash)"]
        DUAL --> FLTR{"Filter: --only-indexed?"}
        FLTR -- "Enabled" --> STRCT["Retain ONLY Scopus / WoS Confirmed"]
        FLTR -- "Disabled" --> BROAD["Retain All Confirmed Academic Citations"]
    end

    subgraph Out["📊 4. Analysis, Export & Cloud Synchronization"]
        STRCT & BROAD --> ANL["Taxonomy & Learning Classifier (37 Fields)"]
        ANL --> CSV["Standardized UTF-8 BOM CSV (csv_builder.py)\n(RFC 4180 Escaping, Validated JSON Verified Sources)"]
        CSV --> GDRV["Google Drive v3 (supportsAllDrives=True)\n(Target Shared Drive / Shared Folder)"]
        CSV --> RPT["Gmail Completion Report (Attached CSV + Metrics)"]
        CSV --> DB["SQLite: Log Metrics & Mark daily_run_completed"]
        CSV --> PURGE["🧹 Cache Maintenance: Nightly 00:00 Purge"]
    end
```

---

## 2. 📁 Modular Directory Architecture

The codebase adheres strictly to the **Single-Responsibility Principle (SRP)**. Monolithic files have been decomposed into isolated packages and client modules:

```
The_Paper_Getter/
├── .env                              # Production credentials (S2_API_KEY, SMTP, Drive) - Never committed
├── .env.example                      # Template configuration with all parameter placeholders
├── .gitignore                        # Git exclusion rules (.env, *.db, service_account.json)
├── config/                           # Centralized Configuration & Environment Loader
│   ├── __init__.py                   # Package re-exports: cfg, PipelineConfig, constants
│   ├── env.py                        # .env loading logic and candidate path resolution
│   ├── constants.py                  # Rate limits, operational quotas, timeouts, TTL values
│   └── settings.py                   # PipelineConfig dataclass, singleton 'cfg', headers generator
├── services/
│   ├── academic/                     # Isolated Academic API Clients
│   │   ├── __init__.py               # Re-exports: SemanticScholarClient, CrossrefClient, etc.
│   │   ├── semantic_scholar.py       # S2 Graph API client (Strict 1 req/s + 429 exponential backoff)
│   │   ├── crossref.py               # Crossref REST client (50 req/s polite pool + mailto header)
│   │   ├── openalex.py               # OpenAlex API client (10 req/s + CC0 registry metadata)
│   │   └── arxiv.py                  # arXiv Atom XML client (3.0s polite delay + preprint parsing)
│   ├── cache/                        # Caching Layer & Automated Maintenance
│   │   ├── __init__.py               # Re-exports: CacheManager, purge_stale_cache, purge_nightly_cache
│   │   ├── ttl.py                    # CacheTTLPolicy (48h verification TTL, 24h query TTL)
│   │   ├── manager.py                # CacheManager (SHA-256 key hashing, JSON read/write)
│   │   └── cleaner.py                # Automated maintenance engine (00:00 midnight purge & --clear-cache)
│   ├── drive/                        # Google Drive Cloud Storage & Quota Management
│   │   ├── __init__.py               # Re-exports: GoogleDriveClient, drive_client
│   │   ├── client.py                 # Drive API v3 uploader (supportsAllDrives=True, chunked streams)
│   │   ├── quota.py                  # Service account 403 quota error prevention and diagnostics
│   │   └── mime.py                   # MIME type detection and optional gzip compression
│   └── notifications/                # Email Dispatch, IMAP Ingestion & Templates
│       ├── __init__.py               # Re-exports: EmailDispatcher, email_dispatcher, imap_reader
│       ├── tag_parser.py             # Resilient 15-tag regex configuration parser & boundary checks
│       ├── templates.py              # HTML responsive email cards and plain-text templates
│       ├── dispatcher.py             # High-level EmailDispatcher with fail-safe error handling
│       ├── smtp_dispatcher.py        # Gmail SMTP transport with STARTTLS & MIME attachments
│       ├── mailgun_dispatcher.py     # Mailgun REST API transport
│       ├── sendgrid_dispatcher.py    # SendGrid v3 Web API transport
│       └── imap_listener.py          # IMAP inbox poller for incoming questionnaire replies
├── utils/                            # Shared Utilities & Decorators
│   ├── __init__.py                   # Re-exports: TokenBucketRateLimiter, sanitizers, retries
│   ├── rate_limiters.py              # TokenBucketRateLimiter (thread-safe, configurable buffer)
│   ├── retry_handlers.py             # execute_with_429_retry (HTTP 429 exponential backoff)
│   └── converters.py                 # sanitize_doi, sanitize_title, clean_matching_title, clean_year
├── harvester/                        # Multi-Provider Asynchronous Accumulator
│   ├── base.py                       # BaseAsyncHarvester with rate limiting and retry logic
│   ├── models.py                     # Paper dataclass with 37 standardized attributes
│   ├── deduplication.py              # Exact canonical DOI + 90% fuzzy SequenceMatcher deduplication
│   └── pipeline.py                   # AsyncHarvestingPipeline (83/87 freezing bug fix)
├── verifier/                         # Multi-Source Academic Verification Engine
│   ├── circuit_breaker.py            # Circuit breaker tripping on 401/403/429
│   ├── dual_branch.py                # Concurrent ThreadPoolExecutor querying across all 7 sources
│   ├── scopus.py                     # Elsevier Scopus API client with token pool rotation
│   ├── wos.py                        # Clarivate Web of Science client with token rotation
│   ├── ieee.py                       # IEEE Xplore API client with token rotation
│   └── cache.py                      # Persistent JSON verification response cache
├── analyzer.py                       # 37-Taxonomy Machine Learning classifier
├── csv_builder.py                    # Standardized UTF-8 BOM CSV exporter (RFC 4180 compliant)
├── excel_builder.py                  # Standardized Excel exporter (.xlsx with Rows 1-10 audit metadata)
├── batch_runner.py                   # Deterministic alphabetical batch runner for input/ datasets
├── database.py                       # SQLite state storage (pipeline.db)
├── scheduler.py                      # 3-tier IST reminder daemon (07:30, 14:00, 21:00) & IMAP listener
├── main.py                           # Central CLI entrypoint and interactive terminal intake
└── tests/                            # Automated Unit Test Suite (34 comprehensive tests)
```

---

## 3. ❓ Question-by-Question Deep Dive (15-Point Intake)

Every interactive prompt in `main.py` and email tag in `email_service.py` serves a deliberate architectural purpose. Below is the exhaustive breakdown of all 15 intake questions:

---

### Question 1: Run Name / Query Identifier
- **Terminal Prompt:** `[1/15] Run Name (Press Enter for auto timestamp):`
- **Email Tag:** `[NAME_OF_RUN]: Run_YYYYMMDD_01`
- **CLI Flag:** `--run-name <identifier>`
- **Underlying Rationale:**
  Maintains end-to-end data provenance. The pipeline processes hundreds of academic records per execution. Establishing an immutable run identifier ensures that output filenames, Google Drive asset titles, email notifications, and SQLite database audit logs share an identical identifier.
- **Default / Recommended Behavior:**
  Pressing Enter defaults to `Run_YYYYMMDD_HHMMSS` (e.g., `Run_20261029_083000`). If received via scheduled morning email, it defaults to `Run_YYYYMMDD_01`.
- **Follow-Up Handling & Downstream Branching:**
  1. Primary CSV output is written to: `output/{run_name}.csv`.
  2. Uploaded to Google Drive with `custom_filename="{run_name}.csv"`.
  3. Formatted into the email subject: `✅ [Harvest Complete] {run_name} — {count} Papers Verified & Synced!`.
  4. Stored as the primary key in SQLite: `db.log_run_start(run_id, run_name, run_config)`.

---

### Question 2: Type of Run
- **Terminal Prompt:** `[2/15] Type of Run: [1] Automated Scheduled  [2] Spontaneous Manual  [3] Batch File Run`
- **Email Tag:** `[RUN_TYPE]: Automated | Manual | Batch`
- **Underlying Rationale:**
  Configures the execution runtime lifecycle and logging verbosity.
- **Selectable Choices:**
  - `[1] Automated Scheduled`: Headless background execution triggered by the 3-tier IST reminder daemon (`scheduler.py`). Suppresses console blocking prompts.
  - `[2] Spontaneous Manual (Default)`: Interactive single-topic search launched directly from terminal.
  - `[3] Batch File Run`: Ingests pre-existing candidate datasets from `input/` folder in alphabetical order.
- **Downstream Branching:**
  Selecting `[3]` terminates single-topic query intake and immediately launches [`ResilientBatchRunner`](file:///c:/Users/rohan/Documents/##%20Code/5)%20October%20-%202026/The_Paper_Getter/batch_runner.py).

---

### Question 3: Execution Location
- **Terminal Prompt:** `[3/15] Execution Location: [1] HITS Campus  [2] Home  [3] Online Remote VPS`
- **Email Tag:** `[LOCATION]: HITS Campus | Home | Online VPS`
- **Underlying Rationale:**
  Elsevier Scopus and Clarivate Web of Science enforce institutional IP-range authentication. Capturing the host environment enables the verifier to determine whether campus IP authentication will succeed or if commercial keys will require explicit institutional tokens (`ELSEVIER_INST_TOKEN`).
- **Options Breakdown:**
  - `[1] HITS Campus`: University campus network. Enables institutional IP recognition.
  - `[2] Home (Default)`: Residential off-campus connection. Automatically prepares Branch 2 Open Access fallbacks if institutional tokens are invalid.
  - `[3] Online Remote VPS`: Cloud servers (e.g. AWS, DigitalOcean). Prevents wasteful IP-authentication attempts and routes to token/Open Access modes.

---

### Question 4 & 5: Batch Execution & Batch Details
- **Terminal Prompt:** `[4/15] Batch Execution across all input files? (y/N):`
- **Email Tag:** `[BATCH_RUN]: Yes | No` / `[BATCH_DETAILS]: <filename>`
- **CLI Flag:** `--all`, `--batch`
- **Underlying Rationale:**
  Allows unattended ingestion of multiple raw CSV citation dumps.
- **Default Behavior:**
  Default is `No`. When `Yes`, the batch runner processes `input/*.csv` strictly alphabetically, skips zero-byte files, maps arbitrary column headers (`DOI`, `Title`, `Abstract`) to canonical models, and exports `{stem}_verified.csv`.

---

### Question 6 & 7: Output Mode & Target Sheet
- **Terminal Prompt:** Output format and destination configuration.
- **Email Tag:** `[OUTPUT_MODE]: Create New | Append to Existing` / `[TARGET_SHEET]: <name>`
- **Underlying Rationale:**
  Determines whether each execution creates an independent dataset or appends records to an existing master spreadsheet.
- **Default Behavior:**
  `Create New` is the standard mode. It outputs a standardized UTF-8 CSV with all 37 columns and RFC 4180 escaping.

---

### Question 8: Main Topic & Topic Count
- **Terminal Prompt:** `[8 & 9/15] Enter Main Topic (e.g. Fuzzy Logic & Neural Networks):`
- **Email Tag:** `[TOPIC_COUNT]: 2` followed by `[TOPIC_1]..[TOPIC_5]`
- **CLI Flag:** `--query "<topic>"`
- **Underlying Rationale:**
  Serves as the root lexical query string for literature harvesting across OpenAlex, Crossref, Semantic Scholar, and arXiv.
- **Boundary Limits:**
  - Maximum topics per run: **5** (hard-capped to protect API rate caps).
- **Default Behavior:**
  Defaults to `fuzzy logic` if submitted blank.

---

### Question 9: Subtopics per Topic
- **Terminal Prompt:** `Enter up to 5 subtopics (comma separated, or press Enter):`
- **Email Tag:** `[T1_SUBTOPICS]: T-Norms, Type-2 Fuzzy Logic, Neuro-Fuzzy Systems`
- **Underlying Rationale:**
  Broad search terms yield high false-positive rates. Specifying subtopics narrows search vectors across aggregators and improves taxonomic classifier scoring.
- **Boundary Limits:**
  - Maximum subtopics per topic: **5**. Excess subtopics trigger an automated corrective notice.

---

### Question 10: Target Quota per Topic
- **Terminal Prompt:** `[10/15] Target Quota per topic [100, 250, 500] (default: 250):`
- **Email Tag:** `[PAPERS_PER_TOPIC]: 100 | 250 | 500`
- **CLI Flag:** `--quota <int>`
- **Underlying Rationale:**
  Defines the exact number of unique, deduplicated, and verified papers to harvest before terminating the active accumulator loop.
- **Boundary Limits:**
  - Hard cap: **500 papers per topic** to prevent remote API blocks.

---

### Question 11: Year Range
- **Terminal Prompt:** `[11/15] Year Range (e.g. 2021-2026 or Enter for All Years):`
- **Email Tag:** `[YEAR_RANGE]: 2021-2026 | All Years`
- **Underlying Rationale:**
  Restricts literature searches to recent state-of-the-art work or includes historical foundational literature.
- **Downstream Branching:**
  Dynamically maps into remote API filters:
  - OpenAlex: `filter=publication_year:2021-2026`
  - Crossref: `filter=from-pub-date:2021-01-01,until-pub-date:2026-12-31`
  - Semantic Scholar: `year=2021-2026`

---

### Question 12: Document Type Filter
- **Terminal Prompt:** `[12/15] Document Filter: [1] All  [2] Journal Articles  [3] Conferences  [4] Preprints`
- **Email Tag:** `[DOC_TYPE]: Journal Articles Only | Conference Proceedings | Preprints | All`
- **Options Breakdown:**
  1. `[1] All`: Includes all document types.
  2. `[2] Journal Articles Only (Default)`: Retains peer-reviewed journal papers.
  3. `[3] Conference Proceedings`: Focuses on proceedings (IEEE, ACM, Springer LNCS).
  4. `[4] Preprints`: Focuses on arXiv, bioRxiv, and OpenAlex preprints.

---

### Question 13: Institutional Token Enablement
- **Terminal Prompt:** `[13/15] Enable Institutional Token (Scopus/WoS/IEEE)? (y/N):`
- **Email Tag:** `[INST_TOKEN]: True | False`
- **Underlying Rationale:**
  Directs the verification engine to attempt Branch 1 commercial APIs (Scopus, WoS, IEEE) or proceed directly to Branch 2 Open Access verification.
- **Default Behavior:**
  `True` if `ELSEVIER_API_KEY` and `ELSEVIER_INST_TOKEN` are populated in `.env`; otherwise `False`.

---

### Question 14: Strict Indexing Filter (`--only-indexed`)
- **Terminal Prompt:** `[14/15] Filter for indexed-only papers (Scopus / Web of Science)? [y/N]:`
- **Email Tag:** `[ONLY_INDEXED]: True | False`
- **CLI Flag:** `--only-indexed`
- **Underlying Rationale:**
  Ensures that retained citations strictly meet university or tenure requirements requiring Scopus or Web of Science indexing.
- **Downstream Branching:**
  - `True (Strict)`: Drops any paper not authoritatively confirmed by Scopus or Web of Science. Increments `excluded_non_indexed` metric.
  - `False (Broad Default)`: Retains citations validated by OpenAlex, Crossref, Semantic Scholar, or arXiv even if commercial indexing is absent.

---

### Question 15: Quota Strictness
- **Terminal Prompt:** `[15/15] Quota Strictness: [1] Strict (Paginate until quota met)  [2] Fast/Capped`
- **Email Tag:** `[QUOTA_STRICTNESS]: Strict | Fast-Capped`
- **Underlying Rationale:**
  Controls the persistence of the active accumulator loop.
- **Options Breakdown:**
  - `Strict (Default)`: Paginates across providers until `len(unique_papers) >= target_quota` or provider catalogs are genuinely exhausted. **Completely eliminates the 83/87 item freezing bug.**
  - `Fast-Capped`: Stops immediately after the initial harvest round regardless of deficit. Useful for quick testing.

---

## 4. 🎯 Multiple-Choice Questions (MCQ) & Filters Breakdown

### Trade-Off Matrix: Speed vs. Coverage vs. Quota Impact

| Configuration Choice | Speed / Latency | Academic Coverage | API Quota Impact | Recommended Use Case |
|---|---|---|---|---|
| **Quota: 100** | ⚡ Very Fast (~15–25s) | Core citations only | Low | Daily topic checks, quick exploratory searches |
| **Quota: 250 (Default)** | ⚖️ Moderate (~45–90s) | Broad domain coverage | Balanced | Systematic reviews, thesis literature surveys |
| **Quota: 500 (Hard Cap)**| 🐢 Slow (~2–4m) | Deep archival catalog | High | Exhaustive bibliographies, longitudinal meta-analyses |
| **Strict Indexing: True** | ⚖️ Moderate | Strict (Scopus/WoS only) | Moderate | Official publication submissions, tenure audits |
| **Strict Indexing: False**| ⚡ Fast | Broad (OA, Preprints, IEEE) | Low | Comprehensive research exploration, preprint discovery |
| **Strictness: Strict** | ⚖️ Moderate | Guaranteed Quota | Full | Automated overnight batches, definitive datasets |
| **Strictness: Fast-Capped**| ⚡ Very Fast | Capped to Round 1 | Minimal | Local debugging, syntax and pipeline smoke tests |

---

### Concrete Output Record Samples

#### Sample A: Strict Indexing Enabled (`--only-indexed`)
```csv
Title,Authors,Year,Publication Type,Venue,DOI,URL,Scopus Indexed,WoS Indexed,IEEE Indexed,Open Access,Verification Source,Verified Sources
"Adaptive Neuro-Fuzzy Inference Systems for Clinical Diagnosis","Rahman, M.; Smith, J.","2024","Journal Article","IEEE Transactions on Fuzzy Systems","10.1109/TFUZZ.2024.1234567","https://doi.org/10.1109/TFUZZ.2024.1234567","Y","Y","Y","N","Scopus API","[""Scopus"", ""Web of Science"", ""IEEE Xplore"", ""Crossref""]"
```

#### Sample B: Broad Open Access Fallback (`--only-indexed` Disabled)
```csv
Title,Authors,Year,Publication Type,Venue,DOI,URL,Scopus Indexed,WoS Indexed,IEEE Indexed,Open Access,Verification Source,Verified Sources
"A Novel Fuzzy Approach to Neural Architecture Search","Zhang, L.; Patel, K.","2024","Preprint","arXiv Preprint","10.48550/arXiv.2401.99999","https://arxiv.org/abs/2401.99999","N","N","N","Y","Open Access Fallback","[""arXiv"", ""OpenAlex"", ""Semantic Scholar""]"
```

---

## 5. ⚡ API Configuration, Rate Limiting & Concurrency Compliance

### Semantic Scholar Strict 1 req/sec Architecture
Semantic Scholar enforces strict rate limits on authenticated and unauthenticated queries. Credentials are read strictly from `.env` via the key:
```bash
S2_API_KEY=s2k-vzrGP8XJrEi2kKHndpXUmiXTvpftTbF9izKpBWUL
```

#### Mathematical Rate Limiting & Token Bucket Formulation
The process-wide rate limiter enforces that for any two consecutive requests $R_i$ and $R_{i+1}$, the inter-request time delta satisfies:
$$\Delta t = t(R_{i+1}) - t(R_i) \ge \frac{1}{\text{rate}} + \delta_{\text{safety}}$$
With $\text{rate} = 1.0\text{ req/sec}$ and $\delta_{\text{safety}} = 0.05\text{s}$, the minimum interval is strictly:
$$\Delta t \ge 1.05\text{ seconds}$$

```python
# services/academic/semantic_scholar.py
_S2_RATE_LIMITER = TokenBucketRateLimiter(rate_limit_per_second=1.0, safety_buffer_seconds=0.05)
```

#### HTTP 429 Exponential Backoff & Retry Mechanism
If a remote rate limit spike occurs, the request is intercepted by [`execute_with_429_retry`](file:///c:/Users/rohan/Documents/##%20Code/5)%20October%20-%202026/The_Paper_Getter/utils/retry_handlers.py):
1. Detects `resp.status_code == 429`.
2. Inspects `Retry-After` header. If provided, sets sleep duration directly to $\text{Retry-After}$.
3. If absent, applies exponential backoff with random jitter:
   $$t_{\text{sleep}} = \min\left(30.0, 1.5 \times 2^{\text{attempt}-1} + \mathcal{U}(0.1, 0.5)\right)$$
4. If multiple keys are configured in `SEMANTIC_SCHOLAR_API_KEYS`, automatically rotates to an unthrottled key.

#### Outbound Header Compliance & Token Pooling
Every outbound request dispatched by [`SemanticScholarClient`](file:///c:/Users/rohan/Documents/##%20Code/5)%20October%20-%202026/The_Paper_Getter/services/academic/semantic_scholar.py) contains:
```python
headers = {
    "User-Agent": cfg.USER_AGENT,
    "Accept": "application/json",
    "x-api-key": os.getenv("S2_API_KEY")
}
```

---

### Multi-Provider Polite Pool & Rate Caps

- **arXiv Atom XML:** Enforces a strict **3.10-second polite delay** between successive requests (`cfg.ARXIV_RATE_DELAY = 3.0`). Parses XML Atom feeds (`entry`, `title`, `published`, `link`) and extracts direct PDF URLs.
- **Crossref Works API:** Operates at up to **50.0 requests per second** by attaching polite pool headers: `User-Agent: AcademicHarvester/4.0 (mailto:{POLITE_EMAIL})`.
- **OpenAlex REST API:** Operates at **10.0 requests per second** with CC0 registry metadata resolution.

---

## 6. 🌙 Automated Nightly Cache Invalidation & Maintenance

### Midnight 00:00 IST Automated Purge Routine
At midnight Indian Standard Time (00:00 IST), the [`ThreeTierScheduler`](file:///c:/Users/rohan/Documents/##%20Code/5)%20October%20-%202026/The_Paper_Getter/scheduler.py) detects the date rollover:
1. Resets SQLite daily run state: `db.reset_daily_state_for_midnight(date_str)`.
2. Automatically executes [`purge_nightly_cache()`](file:///c:/Users/rohan/Documents/##%20Code/5)%20October%20-%202026/The_Paper_Getter/services/cache/cleaner.py).
3. Sweeps `cache/`, `temp/`, and `logs/` directories, permanently unlinking transient citation artifacts older than 24 hours. This guarantees that stale citation data does not persist into the following day's research intake.

### TTL Eviction Hierarchy
```
┌──────────────────────────────────────┬──────────────────────┬────────────────────────┐
│ Cache Category                       │ TTL Threshold        │ Eviction Trigger       │
├──────────────────────────────────────┼──────────────────────┼────────────────────────┤
│ Temporary Query Artifacts & Dumps    │ 24 Hours             │ Nightly 00:00 IST      │
│ API Verification JSON Records        │ 48 Hours             │ Run Completion / TTL   │
│ On-Demand Manual Flush               │ 0 Seconds (All)      │ CLI --clear-cache      │
└──────────────────────────────────────┴──────────────────────┴────────────────────────┘
```

### Manual CLI Cache Flushing (`--clear-cache`)
Users can flush the entire cache directory on demand using either `--clear-cache` or `--clean-cache`:
```bash
python main.py --clear-cache
```

---

## 7. ☁️ Google Drive Cloud Storage & 403 Quota Resolution

### Root Cause of the 403 Storage Quota Error
When uploading files using a Google Cloud Service Account, attempting to upload without specifying a folder (`parents=[folder_id]`) triggers:
```
HttpError 403: The user's Drive storage quota has been exceeded.
```
**Why this happens:** Google Service Accounts do not own personal Google Drive storage (storage quota = 0 MB). Files must be placed into a shared space owned by a real Google user or Google Workspace organization.

---

### Architectural Solutions

#### Option A (Recommended): Google Shared Drive (Team Drive)
Target a Google Shared Drive where the service account email is added as a **Content Manager** or **Contributor**:
1. Open the Google Shared Drive in your browser.
2. Click **Manage Members** and add `your-service-account@project.iam.gserviceaccount.com`.
3. Copy the Shared Drive ID from the URL and set it in `.env`:
   ```bash
   GDRIVE_SHARED_DRIVE_ID=0AFxxx...
   GDRIVE_FOLDER_ID=0AFxxx...
   ```
4. All API requests automatically pass `supportsAllDrives=True`.

#### Option B: Personal Google Drive Shared Folder
Target a folder on a standard personal Google Drive:
1. Create a folder in your personal Google Drive (e.g. `Research_Papers`).
2. Right-click the folder $\rightarrow$ **Share** $\rightarrow$ Add `your-service-account@project.iam.gserviceaccount.com` with **Editor** permissions.
3. Copy the folder ID from the URL and set it in `.env`:
   ```bash
   GDRIVE_FOLDER_ID=1A2B3C...
   ```
4. [`DriveSyncClient`](file:///c:/Users/rohan/Documents/##%20Code/5)%20October%20-%202026/The_Paper_Getter/services/drive/client.py) explicitly attaches `parents=[GDRIVE_FOLDER_ID]` to the upload body. If `GDRIVE_FOLDER_ID` is missing, the client aborts safely before Google API rejection.

#### Option C: User-Level OAuth 2.0 Credentials
Switch from service account authentication to standard user-level OAuth 2.0:
```bash
GDRIVE_REFRESH_TOKEN=1//04xxx...
GDRIVE_CLIENT_ID=xxx.apps.googleusercontent.com
GDRIVE_CLIENT_SECRET=GOCSPX-xxx...
```

---

### Payload Size Tracking & Gzip Compression
- **Target Size Range:** Harvested paper exports typically range between 5 KB and 400 KB.
- **Chunked Resumable Upload:** The pipeline uses `MediaFileUpload(resumable=True)` to stream files cleanly.
- **Optional Gzip Compression:** When remote transport bandwidth is constrained, enabling `GDRIVE_ENABLE_GZIP=true` compresses `.csv` files into `.csv.gz`, achieving an 80–90% reduction in transfer payload size.

---

## 8. 📋 Standardized 37-Column UTF-8 CSV Schema

Output files generated by [`StandardizedCsvBuilder`](file:///c:/Users/rohan/Documents/##%20Code/5)%20October%20-%202026/The_Paper_Getter/csv_builder.py) strictly follow this 37-column field order with UTF-8 BOM (`utf-8-sig`) encoding:

| # | Field Name | Description | Example Value |
|---|---|---|---|
| 1 | `Material ID` | Unique dataset material code | `MAT-001` |
| 2 | `Paper Title` | Sanitized publication title | `Adaptive Neuro-Fuzzy Inference Systems` |
| 3 | `Authors` | Semicolon-delimited author names | `Jang, J.-S. R.; Sun, C.-T.` |
| 4 | `Publication Year` | 4-digit publication year | `2024` |
| 5 | `Publication Type` | Publication format category | `Journal Article` |
| 6 | `Journal / Conference / Venue Name` | Full venue name | `IEEE Transactions on Systems, Man, and Cybernetics` |
| 7 | `DOI` | Canonical lowercase DOI | `10.1109/21.256541` |
| 8 | `Permanent URL / Publisher Link` | Web resolver URL | `https://doi.org/10.1109/21.256541` |
| 9 | `Open Access Direct PDF Link` | Direct PDF link if OA | `https://arxiv.org/pdf/2401.12345.pdf` |
| 10 | `Harvest Source Engine` | Discovery engine name | `OpenAlex` |
| 11 | `Main Problem Addressed` | Core research objective | `Nonlinear system identification under uncertainty` |
| 12 | `Main Practical Application` | Domain deployment area | `Biomedical EEG signal classification` |
| 13 | `Importance Level` | Importance classification | `High` |
| 14 | `Learning Level` | Complexity rating | `Intermediate` |
| 15 | `Primary Category ID` | Primary taxonomy code | `CAT-04` |
| 16 | `Primary Category Name` | Primary taxonomy name | `Neuro-Fuzzy Learning & Tuning` |
| 17 | `Secondary Category 1 ID` | Cross-domain code 1 | `CAT-02` |
| 18 | `Secondary Category 1 Name` | Cross-domain name 1 | `Type-2 Fuzzy Logic Systems` |
| 19 | `Secondary Category 2 ID` | Cross-domain code 2 | `CAT-08` |
| 20 | `Secondary Category 2 Name` | Cross-domain name 2 | `Explainable AI & Rule Extraction` |
| 21 | `Secondary Category 3 ID` | Cross-domain code 3 | `CAT-11` |
| 22 | `Secondary Category 3 Name` | Cross-domain name 3 | `Biomedical Applications` |
| 23 | `Secondary Category 4 ID` | Cross-domain code 4 | `N/A` |
| 24 | `Secondary Category 4 Name` | Cross-domain name 4 | `None` |
| 25 | `Secondary Category 5 ID` | Cross-domain code 5 | `N/A` |
| 26 | `Secondary Category 5 Name` | Cross-domain name 5 | `None` |
| 27 | `Current Research Status` | Literature workflow status | `Identified` |
| 28 | `Current Reading Status` | Reading review status | `Not Started` |
| 29 | `Scopus Indexed` | Scopus verification boolean | `Y` |
| 30 | `Web of Science Indexed` | WoS verification boolean | `Y` |
| 31 | `IEEE Xplore Indexed` | IEEE verification boolean | `Y` |
| 32 | `Open Access` | Open Access status boolean | `N` |
| 33 | `Relevance Score` | Computed relevance (1-10) | `10` |
| 34 | `Abstract Summary` | Sanitized multiline abstract | `This study presents an adaptive architecture...` |
| 35 | `Researcher Notes` | Internal remarks / tags | `Foundational citation for Section 3 methodology` |
| 36 | `Date Added to Database` | Ingestion timestamp | `2026-10-29` |
| 37 | `Verified Sources` | JSON array of verifying sources | `["Scopus", "Web of Science", "IEEE Xplore", "Crossref"]` |

---

### RFC 4180 Escaping Rules & Excel Compatibility
To guarantee that files open seamlessly in Microsoft Excel, Google Sheets, LibreOffice, and Pandas without delimiter corruption:
1. **UTF-8 with BOM (`utf-8-sig`):** Excel on Windows assumes the ANSI code page unless the 3-byte UTF-8 Byte Order Mark (`\xef\xbb\xbf`) is present. All exported CSVs prepend the BOM so Greek letters ($\alpha, \beta, \theta$), mathematical symbols, and diacritics render perfectly.
2. **RFC 4180 Quotes & Line Breaks:** Any cell value containing a comma, a newline, or a quotation mark is enclosed in double quotes. Internal quotation marks are escaped by doubling them (`""`).

---

## 9. 🔬 Deduplication & Fuzzy Title Matching Algorithm

### Two-Stage Deduplication Architecture
The deduplication engine executes two complementary matching layers to ensure no duplicate papers enter the pipeline:

1. **Stage 1: Canonical DOI Matching ($O(1)$ Hash Set)**
   - Every incoming DOI is normalized via `sanitize_doi()`: converts to lowercase, strips URL resolvers (`https://doi.org/`, `doi:`), and removes trailing punctuation.
   - If `clean_doi` already exists in `seen_dois`, the record is instantly discarded as a duplicate.

2. **Stage 2: Inverted Token Bucketing & SequenceMatcher ($O(K)$ Match)**
   - For papers lacking a DOI or preprints possessing distinct IDs, the engine extracts significant alphanumeric tokens ($\ge 4$ characters) from the sanitized title.
   - Using an inverted index (`token_buckets`), the candidate paper is only compared against existing papers that share at least one keyword token.
   - The title similarity ratio is computed using Ratcliff/Obershelp gestalt pattern matching:
     $$\text{ratio} = \frac{2M}{T_1 + T_2}$$
     where $M$ is the number of matching characters, and $T_1, T_2$ are the total lengths of the respective titles.
   - If $\text{ratio} \ge 0.90$ (90% threshold), the candidate is dropped as a duplicate.

---

## 10. 🚀 Complete Beginner's Walkthrough

### Step 1: Generating the Gmail 16-Character App Password
1. Visit your [Google Account Security Settings](https://myaccount.google.com/security).
2. Ensure **2-Step Verification** is turned **ON**.
3. Under *2-Step Verification*, scroll down to **App Passwords**.
4. Create a new App Password:
   - App Name: `Academic Harvester`
5. Google will display a 16-character code (e.g., `abcd efgh ijkl mnop`).
6. Copy this code and set it as `SMTP_PASSWORD` and `IMAP_PASSWORD` in `.env`.

### Step 2: Enabling IMAP in Gmail Settings
1. Open Gmail in your web browser.
2. Click the gear icon $\rightarrow$ **See all settings** $\rightarrow$ **Forwarding and POP/IMAP**.
3. Under *IMAP Access*, select **Enable IMAP**.
4. Click **Save Changes** at the bottom.

### Step 3: Setting Up Google Drive API & Service Account
1. Open [Google Cloud Console](https://console.cloud.google.com/).
2. Create a project: `Academic-Paper-Harvester`.
3. Enable the **Google Drive API**.
4. Navigate to **IAM & Admin** $\rightarrow$ **Service Accounts** $\rightarrow$ **Create Service Account**.
5. Once created, click on the Service Account $\rightarrow$ **Keys** tab $\rightarrow$ **Add Key** $\rightarrow$ **Create new key (JSON)**.
6. Rename the downloaded file to `service_account.json` and place it in the project root.
7. Share your Google Drive target folder or Shared Drive with the service account email (with **Editor** permissions).

### Step 4: Configuring the `.env` File
Create `.env` based on `.env.example`:
```bash
POLITE_EMAIL=researcher@university.edu
S2_API_KEY=s2k-vzrGP8XJrEi2kKHndpXUmiXTvpftTbF9izKpBWUL
SMTP_USER=researcher@gmail.com
SMTP_PASSWORD=abcd efgh ijkl mnop
IMAP_USER=researcher@gmail.com
IMAP_PASSWORD=abcd efgh ijkl mnop
GDRIVE_FOLDER_ID=1A2B3C...
GDRIVE_SERVICE_ACCOUNT_JSON=service_account.json
```

### Step 5: Testing Local Connectivity
Verify all components using the automated test suite:
```bash
python main.py --test
```

---

## 11. 🛡️ Troubleshooting & Failure Recovery Matrix

### Scenario A: Elsevier Scopus 401/403 Authentication Failure
- **Symptom:** Terminal displays `[Scopus] HTTP 401 Unauthorized`.
- **Root Cause:** User is executing from off-campus broadband and `ELSEVIER_INST_TOKEN` is missing or expired.
- **Fail-Safe Recovery:**
  1. Circuit breaker trips immediately upon detecting the 401/403 error.
  2. The verifier routes the paper to Branch 2 Open Access fallbacks.
  3. Scopus index status is checked against local offline ISSN database (`data/scopus_source_list.xlsx`).
  4. Pipeline continues execution without crashing.

### Scenario B: Semantic Scholar HTTP 429 Throttle Spike
- **Symptom:** `⚠️ [Semantic Scholar] HTTP 429 (Rate Limit Hit). Backing off for 3.12s...`
- **Root Cause:** Transient server-side queue pressure or concurrent burst traffic.
- **Fail-Safe Recovery:**
  1. `execute_with_429_retry` pauses the thread for the exponential backoff duration.
  2. If multiple keys exist in `SEMANTIC_SCHOLAR_API_KEYS`, automatically rotates to an alternative key.
  3. Upon retry, the request succeeds and processing resumes.

### Scenario C: Google Drive HttpError 403 Storage Quota Exceeded
- **Symptom:** `HttpError 403: Service Accounts do not have storage quota.`
- **Root Cause:** `GDRIVE_FOLDER_ID` is empty or pointing to personal Drive root.
- **Fail-Safe Recovery:**
  1. The client intercepts the missing folder ID and halts upload safely before Google API rejection.
  2. The local CSV file remains completely intact and accessible under `output/`.
  3. Completion email is dispatched with the CSV attached, logging Drive sync status cleanly.

### Scenario D: SMTP Authentication Rejection (Error 535)
- **Symptom:** `❌ [Email ERROR] SMTP delivery failed: (535, '5.7.8 Username and Password not accepted')`
- **Root Cause:** Standard account password used instead of a 16-character Google App Password.
- **Fail-Safe Recovery:**
  1. Non-crashing exception wrapper catches the error.
  2. Logs warning to terminal and log file.
  3. Google Drive upload and local CSV exports complete successfully without interruption.

### Scenario E: Inbound Email Formatting & Syntax Errors
- **Symptom:** User replies with missing brackets or out-of-bounds quota (`[PAPERS_PER_TOPIC]: 1000`).
- **Root Cause:** Input boundary violation.
- **Fail-Safe Recovery:**
  1. `tag_parser.py` flags the error: `❌ [PAPERS_PER_TOPIC]: Hard ceiling is 500 papers`.
  2. Dispatches an automated corrective email with copy-paste correction blocks.
  3. Awaits user reply without terminating the daemon.

---

## 12. ⚙️ Production Deployment & Headless Daemon Operations

### Linux Systemd Service Setup
To run the 3-tier IST reminder scheduler and IMAP polling listener continuously as a background service on Linux:

```ini
# /etc/systemd/system/paper-harvester.service
[Unit]
Description=Unified Academic Paper Harvester & Reminder Daemon
After=network.target

[Service]
Type=simple
User=researcher
WorkingDirectory=/home/researcher/The_Paper_Getter
ExecStart=/home/researcher/The_Paper_Getter/.venv/bin/python main.py --scheduler
Restart=always
RestartSec=15
EnvironmentFile=/home/researcher/The_Paper_Getter/.env

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable paper-harvester
sudo systemctl start paper-harvester
sudo systemctl status paper-harvester
```

### Windows Task Scheduler & Background Daemon
On Windows systems, the scheduler can be launched in a persistent background session:
```powershell
Start-Process -FilePath ".\.venv\Scripts\python.exe" -ArgumentList "main.py --scheduler" -WindowStyle Hidden
```

### Crontab Configuration
If using standard system `cron` instead of the internal daemon:
```bash
# Purge temporary cache files every night at midnight IST (18:30 UTC)
30 18 * * * cd /home/researcher/The_Paper_Getter && ./.venv/bin/python -m services.cache.cleaner >> logs/cron.log 2>&1

# Check morning intake at 07:30 AM IST (02:00 UTC)
00 02 * * * cd /home/researcher/The_Paper_Getter && ./.venv/bin/python main.py --check-reminders --tier morning >> logs/cron.log 2>&1
```

---

## 13. 🛠️ CLI Reference & Command Index

### Primary CLI Commands
```bash
# 1. Interactive 15-point terminal intake
python main.py

# 2. Spontaneous query harvest with quota
python main.py --query "Fuzzy Logic & Neural Networks" --quota 250 --run-name "Fuzzy_Run_01"

# 3. Filter strictly for Scopus or Web of Science indexed papers
python main.py --query "Graph Neural Networks" --quota 150 --only-indexed

# 4. Batch file execution across input/ directory
python main.py --all --only-indexed

# 5. Launch 3-tier IST reminder scheduler and IMAP polling daemon
python main.py --scheduler

# 6. Flush temporary cache directory on demand
python main.py --clear-cache

# 7. Check and dispatch pending IST reminders immediately
python main.py --check-reminders --tier morning

# 8. Run automated unit test suite
python main.py --test
```
