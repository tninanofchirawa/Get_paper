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
5. [⚡ API Configuration, Token-Bucket Rate Limiting & Active Multi-Source Round-Robin Query Distributor](#5--api-configuration-token-bucket-rate-limiting--active-multi-source-round-robin-query-distributor)
   - [Semantic Scholar Strict 1 req/sec Global Limiter](#semantic-scholar-strict-1-reqsec-global-limiter)
   - [Mathematical Rate Limiting & Token Bucket Formulation](#mathematical-rate-limiting--token-bucket-formulation)
   - [Active Query Distributor & Cross-Provider Round-Robin Rotation](#active-query-distributor--cross-provider-round-robin-rotation)
   - [Dynamic Cooldown Buffer (5.5s) & Exponential Backoff Window](#dynamic-cooldown-buffer-55s--exponential-backoff-window)
   - [Multi-Provider Polite Pool & Rate Caps (OpenAlex, Crossref, arXiv, CORE)](#multi-provider-polite-pool--rate-caps-openalex-crossref-arxiv-core)
6. [🌙 Automated Nightly Cache Invalidation, Compact Data Schema & Footprint Maintenance](#6--automated-nightly-cache-invalidation-compact-data-schema--footprint-maintenance)
   - [Midnight 00:00 IST Automated Purge Routine](#midnight-0000-ist-automated-purge-routine)
   - [Compact "Data-Only" Payload Schema](#compact-data-only-payload-schema)
   - [LRU 30 MB Size-Capped Eviction Engine](#lru-30-mb-size-capped-eviction-engine)
   - [Automated Disk Footprint Profiling (audit_footprint.py / .ps1)](#automated-disk-footprint-profiling-audit_footprintpy--ps1)
   - [Zero-Dependency Safe Artifact Purger (clean.py / clean.ps1)](#zero-dependency-safe-artifact-purger-cleanpy--cleanps1)
7. [☁️ Google Drive Cloud Storage & 403 Storage Quota Resolution](#7-️-google-drive-cloud-storage--403-quota-resolution)
   - [Root Cause of the 403 Storage Quota Error](#root-cause-of-the-403-storage-quota-error)
   - [Method 1: User OAuth 2.0 Credentials (Personal @gmail.com Drives)](#method-1-user-oauth-20-credentials-personal-gmailcom-drives)
   - [Method 2: Google Workspace Shared Drive (Team Drive)](#method-2-google-workspace-shared-drive-team-drive)
   - [Pre-Flight Validation Logging & Storage Mode Detection](#pre-flight-validation-logging--storage-mode-detection)
   - [Payload Size Tracking & Resumable Chunked Streaming](#payload-size-tracking--resumable-chunked-streaming)
8. [📋 Formatted Two-Tier CSV Architecture & 32-Field Analytical Dataset](#8--formatted-two-tier-csv-architecture--32-field-analytical-dataset)
   - [Two-Tier Layout Specification (Rows 1-15 Header Block, Row 16+ Dataset)](#two-tier-layout-specification-rows-1-15-header-block-row-16-dataset)
   - [32 Standard Analytical Fields Breakdown (Columns B through AG)](#32-standard-analytical-fields-breakdown-columns-b-through-ag)
   - [Excel, Google Sheets & Pandas Dual-Tier Compatibility](#excel-google-sheets--pandas-dual-tier-compatibility)
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
   - [Scenario F: Module Migration & Path Resolution After Structural Consolidation](#scenario-f-module-migration--path-resolution-after-structural-consolidation)
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

    subgraph Harv["⚡ 2. Active Round-Robin Accumulator Harvester"]
        PIPE --> DIST["ActiveQueryDistributor (Round-Robin & Dynamic Cooldown)"]
        DIST --> OA["OpenAlex API (10 req/s)"]
        DIST --> CR["Crossref REST (50 req/s polite pool)"]
        DIST --> AR["arXiv Atom XML (3.1s polite delay)"]
        DIST --> SS["Semantic Scholar Graph API (1 req/s Global Token-Bucket)"]
        DIST --> CO["CORE API v3 (Search Aggregator)"]
        OA & CR & AR & SS & CO --> DEDUP["Deduplication Engine\n(Exact DOI + 90% Fuzzy Title Normalization)"]
        DEDUP -- "Rotates Providers until verified >= Quota" --> QUEUE["Unique Candidate Papers Queue"]
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
        STRCT & BROAD --> ANL["Taxonomy & Learning Classifier (32 Fields)"]
        ANL --> CSV["Standardized Two-Tier CSV (csv_builder.py)\n(Tier 1: Rows 1-15 Metadata | Tier 2: Row 16+ Dataset)"]
        CSV --> GDRV["Google Drive v3 (User OAuth 2.0 or Shared Drive)\n(Pre-Flight Storage Quota Validation)"]
        CSV --> RPT["Gmail Completion Report (Attached Two-Tier CSV + Metrics)"]
        CSV --> DB["SQLite: Log Metrics & Mark daily_run_completed"]
        CSV --> PURGE["🧹 Cache Maintenance: Compact Payload, LRU 30MB & 00:00 Purge"]
    end
```

---

## 2. 📁 Modular Directory Architecture

The repository adheres strictly to the **Single-Responsibility Principle (SRP)**, modular clustering, and hierarchical directory nesting. Single-purpose scripts scattered across top-level locations have been organized into purpose-built packages (`core/`, `utils/`, `services/`, `scripts/maintenance/`, `scripts/audit/`), while all runtime data and volatile files have been nested under a unified `storage/` namespace.

Full backward compatibility is maintained via lightweight root shims (`analyzer.py`, `batch_runner.py`, `database.py`, `csv_builder.py`, `excel_builder.py`, `clean.ps1`, `test_email.py`, `cache_cleaner.py`), ensuring that legacy automated routines, scheduled tasks, and command-line scripts run without breakage.

### 2.1 Complete Repository ASCII File Tree

```text
The_Paper_Getter/
├── .env                              # Production credentials & API keys (Never committed to VCS)
├── .env.example                      # Template configuration with all parameter placeholders
├── .gitignore                        # Hardened git exclusion rules (secrets, venvs, storage outputs/caches)
├── clean.ps1                         # Root convenience launcher delegating to scripts/maintenance/clean.ps1
├── analyzer.py                       # Root backward-compatibility shim -> core.analyzer
├── batch_runner.py                   # Root backward-compatibility shim -> core.batch_runner
├── cache_cleaner.py                  # Root backward-compatibility shim -> scripts.maintenance.cache_cleaner
├── credentials.json                  # Google Cloud Desktop App OAuth 2.0 Client Secrets
├── csv_builder.py                    # Root backward-compatibility shim -> utils.csv_builder
├── database.py                       # Root backward-compatibility shim -> core.database
├── drive_sync.py                     # Google Drive CLI sync & OAuth helper -> services.drive
├── email_service.py                  # Root backward-compatibility shim -> services.notifications
├── excel_builder.py                  # Root backward-compatibility shim -> utils.excel_builder
├── main.py                           # Primary CLI entrypoint & interactive 15-question intake engine
├── README.md                         # Project overview and high-level quick start guide
├── requirements.txt                  # Python dependencies (pandas, openpyxl, google-api-python-client, etc.)
├── run.py                            # Non-interactive CLI runner wrapper
├── scheduler.py                      # 3-Tier IST reminder daemon (07:30, 14:00, 21:00) & IMAP listener
├── service_account.json              # Optional Google Workspace Service Account JSON credentials
├── test_email.py                     # Root backward-compatibility shim -> scripts.audit.test_email
├── config/                           # Centralized Configuration & Environment Loader
│   ├── __init__.py                   # Package re-exports: cfg, PipelineConfig, constants
│   ├── constants.py                  # Rate limits, operational quotas, timeouts, TTL values, MAX_CACHE_SIZE_MB
│   ├── env.py                        # .env dynamic candidate path loader keyed from BASE_DIR
│   └── settings.py                   # PipelineConfig dataclass, singleton 'cfg', dynamic storage directory resolution
├── core/                             # Orchestration Engines, Batch Processing & Persistence
│   ├── __init__.py                   # Core re-exports: PaperAnalyzer, ResilientBatchRunner, DatabaseManager, db
│   ├── analyzer.py                   # 37-Taxonomy Fuzzy ML Classifier & NLP heuristic classifier
│   ├── batch_runner.py               # Deterministic alphabetical file queue & failure boundary runner
│   ├── database.py                   # SQLite persistence engine (pipeline.db, daily_state, file_queue)
│   └── models.py                     # Canonical Paper dataclass & title/DOI canonical sanitizers
├── data/                             # Authoritative Local Master Databases
│   ├── pipeline.db                   # SQLite runtime transactional database (WAL mode)
│   ├── scopus_source_list.xlsx       # Elsevier Scopus master source title/ISSN database (44,000+ journals)
│   └── wos_master_journal_list.csv   # Clarivate Web of Science master journal list (24,000+ journals)
├── harvester/                        # Multi-Provider Asynchronous Accumulator
│   ├── __init__.py                   # Harvester re-exports: AsyncHarvestingPipeline, ActiveQueryDistributor
│   ├── arxiv.py                      # arXiv Atom XML harvester (3.1s polite delay)
│   ├── base.py                       # BaseAsyncHarvester with rate limiting and exponential backoff
│   ├── core_ac.py                    # CORE API v3 search harvester
│   ├── crossref.py                   # Crossref REST harvester (50 req/s polite pool)
│   ├── deduplication.py              # Exact canonical DOI + 90% fuzzy SequenceMatcher deduplication
│   ├── distributor.py                # ActiveQueryDistributor: round-robin provider rotation & 5.5s cooldown
│   ├── models.py                     # Paper dataclass with standardized analytical attributes
│   ├── openalex.py                   # OpenAlex REST harvester (10 req/s polite pool)
│   ├── pipeline.py                   # AsyncHarvestingPipeline (Active round-robin query accumulator)
│   └── semantic_scholar.py           # Semantic Scholar harvester (1 req/s global token-bucket)
├── scripts/                          # Diagnostic Utilities, Maintenance Jobs & Profilers
│   ├── __init__.py                   # Package marker for scripts namespace
│   ├── audit_footprint.py            # Backward-compatibility wrapper -> scripts.audit.audit_footprint
│   ├── audit_footprint.ps1           # Backward-compatibility launcher -> scripts/audit/audit_footprint.ps1
│   ├── clean.py                      # Backward-compatibility wrapper -> scripts.maintenance.clean
│   ├── audit/                        # System Auditing & Inspection Utilities
│   │   ├── __init__.py               # Audit package marker
│   │   ├── audit_footprint.py        # Single-pass filesystem disk profiler (Top 10 dirs/files, culprit breakdown)
│   │   ├── audit_footprint.ps1       # Zero-dependency PowerShell footprint profiler
│   │   └── test_email.py             # Visual verification test dispatcher for rich HTML email templates
│   └── maintenance/                  # Safe Maintenance, Purging & Cache Cleaners
│       ├── __init__.py               # Maintenance package marker
│       ├── cache_cleaner.py          # Cache life-cycle purging engine (00:00 purge & TTL eviction)
│       ├── clean.ps1                 # Zero-dependency PowerShell artifact cleaner
│       └── clean.py                  # Zero-dependency artifact cleaner (--dry-run support)
├── services/                         # Isolated Domain & External Integration Services
│   ├── academic/                     # Academic Aggregator Clients & Parsers
│   │   ├── __init__.py               # Re-exports: SemanticScholarClient, OpenAlexClient, CrossrefClient, etc.
│   │   ├── arxiv.py                  # arXiv Atom XML API client (3.0s delay + preprint parsing)
│   │   ├── crossref.py               # Crossref REST API client (50 req/s + polite mailto header)
│   │   ├── doaj.py                   # Directory of Open Access Journals (DOAJ) REST client
│   │   ├── openalex.py               # OpenAlex Works API client (10 req/s + CC0 registry metadata)
│   │   └── semantic_scholar.py       # Semantic Scholar Graph API client (Strict 1 req/s cap)
│   ├── cache/                        # Caching Layer, TTL Policies & Eviction Managers
│   │   ├── __init__.py               # Re-exports: CacheManager, CacheTTLPolicy, purge_stale_cache
│   │   ├── cleaner.py                # Automated maintenance engine (00:00 midnight purge & LRU eviction)
│   │   ├── manager.py                # CacheManager (Compact schema, LRU size cap to 30 MB)
│   │   └── ttl.py                    # CacheTTLPolicy (48h verification TTL, 24h query TTL)
│   ├── drive/                        # Google Drive Cloud Upload & Quota Management
│   │   ├── __init__.py               # Re-exports: GoogleDriveClient, DriveUploader, drive_client
│   │   ├── auth.py                   # OAuth 2.0 authentication entrypoint & token loader
│   │   ├── client.py                 # Drive API v3 client (supportsAllDrives=True, chunked upload)
│   │   ├── mime.py                   # MIME type detection & gzip compression utilities
│   │   ├── oauth.py                  # User OAuth 2.0 flow (Method 1: credentials.json -> token.json)
│   │   ├── quota.py                  # Pre-flight quota check & 403 prevention diagnostics
│   │   └── uploader.py               # Standardized drive uploader handler alias
│   └── notifications/                # Email Dispatch, Alerting & IMAP Listener
│       ├── __init__.py               # Re-exports: EmailDispatcher, Mailer, imap_reader
│       ├── dispatcher.py             # High-level resilient EmailDispatcher with error boundaries
│       ├── imap_listener.py          # IMAP inbox poller for incoming questionnaire responses
│       ├── mailer.py                 # Mailer and alerting interface (alias to EmailDispatcher)
│       ├── mailgun_dispatcher.py     # Mailgun REST API transport
│       ├── sendgrid_dispatcher.py    # SendGrid v3 Web API transport
│       ├── smtp_dispatcher.py        # Gmail SMTP transport with STARTTLS & MIME attachments
│       ├── tag_parser.py             # 15-tag regex configuration parser & sanitizers
│       └── templates.py              # Responsive HTML email templates & plain-text fallbacks
├── storage/                          # Hierarchical Persistent & Runtime Storage Root
│   ├── __init__.py                   # Storage package marker
│   ├── cache/                        # Local response cache JSON dumps (paper_verification_cache.json)
│   ├── input/                        # Input directory for batch candidate CSV files
│   ├── logs/                         # Runtime diagnostic logs and daemon execution logs
│   ├── output/                       # Standardized verified CSV and Excel spreadsheets
│   └── temp/                         # Transient scratch files and chunked buffer streams
├── utils/                            # Shared Utilities, Format Converters & Robustness Primitives
│   ├── __init__.py                   # Re-exports: StandardizedCsvBuilder, StandardizedExcelBuilder, CircuitBreaker
│   ├── circuit_breaker.py            # Circuit breaker tripping on consecutive failures (401/403/429)
│   ├── converters.py                 # String sanitizers, title normalization, and DOI formatters
│   ├── csv_builder.py                # Standardized Two-Tier UTF-8 BOM CSV builder (Rows 1-15 Header, Row 16+ Data)
│   ├── excel_builder.py              # Standardized Production Excel workbook builder (Rows 1-10 Header, Row 11+ Data)
│   ├── rate_limiters.py              # TokenBucketRateLimiter & AsyncRateLimiter primitives
│   └── retry_handlers.py             # Exponential backoff retry decorators & HTTP 429 handlers
├── verifier/                         # Multi-Source Academic Verification & Partitioning Architecture
│   ├── __init__.py                   # Re-exports: TieredWorkloadVerifier, DualBranchVerifier
│   ├── arxiv_verifier.py             # arXiv preprint search and verification
│   ├── cache.py                      # Persistent JSON verification response cache (Compact schema)
│   ├── circuit_breaker.py            # Local circuit breaker wrapper
│   ├── crossref_verifier.py          # Crossref bibliographic & DOI matching
│   ├── doaj_verifier.py              # DOAJ open access journal verification
│   ├── dual_branch.py                # Concurrent ThreadPoolExecutor querying across institutional/open branches
│   ├── ieee.py                       # IEEE Xplore REST verification client
│   ├── local_db.py                   # In-memory O(1) hash matcher for Scopus/WoS source lists
│   ├── local_matcher.py              # Fuzzy ISSN/Title matching algorithms
│   ├── openalex_verifier.py          # OpenAlex Works API matching
│   ├── scopus.py                     # Elsevier Scopus API client with token pool rotation
│   ├── semantic_scholar_verifier.py  # Semantic Scholar Graph API verifier
│   ├── tiered_verifier.py            # TieredWorkloadVerifier (3-way N/3 partition & ring fallback queue)
│   └── wos.py                        # Web of Science API client with token pool rotation
└── tests/                            # Automated Unit & Integration Test Suite (59 comprehensive tests)
    ├── __init__.py                   # Test suite package marker
    ├── test_batch_runner.py          # Deterministic queue & error boundaries test
    ├── test_csv_and_drive.py         # Two-Tier CSV layout & Drive OAuth test
    ├── test_database_and_state.py    # SQLite daily state & WAL mode test
    ├── test_email_and_cache.py       # Email tags, HTML templates & cache cleaner test
    ├── test_excel_builder.py         # Standardized Excel layout test
    ├── test_modular_services.py      # Isolated academic API clients test
    ├── test_rate_limiter.py          # Token-bucket rate limiting test
    ├── test_retry_handlers.py        # Exponential backoff & 429 retry test
    ├── test_structure_consolidation.py # Verification of module clustering & storage hierarchy
    └── test_tiered_verifier.py       # 3-way partitioning & ring fallback queue test
```

---

### 2.2 Module Responsibility Mapping

Every directory and nested subfolder in the consolidated architecture has an explicit, non-overlapping architectural role.

#### 1. `core/` (Orchestration, Batch Processing & Database State)
- **Folder Purpose:** Encapsulates the core business logic, lifecycle execution engines, batch workers, and database transactions governing run histories and candidate records.
- **Contained Modules:**
  - `analyzer.py`: Executes 37-taxonomy Fuzzy Logic & ML classification, heuristic learning level grading, and keyword extraction.
  - `batch_runner.py`: Implements `ResilientBatchRunner` for deterministic alphabetical file queue processing with individual try/except/finally boundaries preventing pipeline task drops.
  - `database.py`: Implements `DatabaseManager` managing SQLite (`pipeline.db`) WAL mode persistence, daily state progression, conversation sessions, and run logs.
  - `models.py`: Defines the canonical `Paper` dataclass and title/DOI sanitization helpers (`clean_matching_title`, `sanitize_doi`).
- **Entry Points:** Core modules are accessed by the pipeline and can be tested or called directly via `from core import ...`.

#### 2. `storage/` (Hierarchical Runtime & Persistent Storage)
- **Folder Purpose:** Consolidates all transient, runtime, and output directories under a single parent namespace, eliminating root-level folder proliferation.
- **Contained Sub-folders:**
  - `storage/cache/`: Houses local JSON response caches (`paper_verification_cache.json`).
  - `storage/output/`: Standard output destination for verified CSV datasets and Excel workbooks.
  - `storage/logs/`: Destination for daemon logs, error traces, and execution telemetry.
  - `storage/temp/`: Transient scratch area for stream buffers and temporary chunks.
  - `storage/input/`: Directory where candidate CSV batches are deposited for batch processing.

#### 3. `services/academic/` (Isolated Aggregator & Indexing Clients)
- **Folder Purpose:** Provides single-purpose, polite API clients for external academic data providers, isolating network formatting, rate limits, and authentication.
- **Contained Modules:**
  - `semantic_scholar.py`: Graph API querying with 1 req/sec strict rate-limiting and 429 retry backoff.
  - `openalex.py`: Works API client leveraging the polite pool mailto header (10 req/sec cap).
  - `crossref.py`: Bibliographic and DOI search client (50 req/sec polite pool cap).
  - `arxiv.py`: Atom XML query client enforcing 3.1-second sequential delay.
  - `doaj.py`: Directory of Open Access Journals REST client for verifying indexed OA publication venues.

#### 4. `services/drive/` (Google Drive Synchronization & Auth)
- **Folder Purpose:** Handles cloud asset synchronization, quota management, and pre-flight validation to prevent HTTP 403 quota errors.
- **Contained Modules:**
  - `auth.py`: Centralized authentication loader wrapping OAuth 2.0 flows.
  - `oauth.py`: Implements Method 1 Desktop OAuth 2.0 (`credentials.json` -> `token.json`) for personal `@gmail.com` accounts.
  - `client.py`: High-level `GoogleDriveClient` with chunked resumable streaming and `supportsAllDrives=True`.
  - `quota.py`: Pre-flight verification routines inspecting target folder IDs, permissions, and service account quotas.
  - `mime.py`: MIME type detection and optional gzip payload compression.
  - `uploader.py`: Alias interface for standardized drive uploading workflows.

#### 5. `services/notifications/` (Email Dispatch, IMAP & Templates)
- **Folder Purpose:** Manages the 100% free Gmail communication lifecycle, parsing incoming configuration tags and rendering rich responsive HTML notifications.
- **Contained Modules:**
  - `mailer.py`: Clean alerting interface re-exporting `EmailDispatcher` as `Mailer`.
  - `dispatcher.py`: High-level dispatch controller with fail-safe error boundaries.
  - `smtp_dispatcher.py`: Gmail SMTP transport with STARTTLS, MIME attachments, and credential validation.
  - `mailgun_dispatcher.py`: Fallback transport for Mailgun REST API.
  - `sendgrid_dispatcher.py`: Fallback transport for SendGrid v3 API.
  - `imap_listener.py`: Background poller reading user configuration emails over IMAP.
  - `tag_parser.py`: Robust regex parser extracting the 15 configuration tags with strict type coercion.
  - `templates.py`: HTML container wrappers, responsive email cards, and plain-text fallbacks.

#### 6. `services/cache/` (Cache Maintenance & Eviction)
- **Folder Purpose:** Enforces cache lifecycle constraints, size ceilings, and scheduled purges.
- **Contained Modules:**
  - `manager.py`: `CacheManager` with SHA-256 keying and 30 MB size-capped LRU eviction.
  - `cleaner.py`: Automated 00:00 IST midnight purge engine and `--clear-cache` handlers.
  - `ttl.py`: `CacheTTLPolicy` defining 48-hour verification TTL and 24-hour query TTL.

#### 7. `utils/` (Converters, Formatters & Robustness Primitives)
- **Folder Purpose:** Shared formatting tools, mathematical rate limiters, resilience decorators, and spreadsheet builders.
- **Contained Modules:**
  - `csv_builder.py`: Implements `StandardizedCsvBuilder` for production two-tier UTF-8 with BOM CSVs (Rows 1-15 header block, Row 16+ data).
  - `excel_builder.py`: Implements `StandardizedExcelBuilder` generating styled `.xlsx` workbooks with Rows 1-10 audit blocks.
  - `circuit_breaker.py`: Circuit breaker pattern preventing API hammering upon consecutive errors.
  - `rate_limiters.py`: Token-bucket and async rate limiters enforcing polite pool limits.
  - `retry_handlers.py`: Exponential backoff decorators handling transient network drops and HTTP 429 throttles.
  - `converters.py`: DOI sanitizers, title cleaners, and year formatters.

#### 8. `scripts/maintenance/` & `scripts/audit/` (Operational Scripts)
- **Folder Purpose:** Isolated diagnostic, maintenance, and administrative scripts separated from production application code.
- **Contained Modules:**
  - `scripts/maintenance/clean.py`: Zero-dependency safe artifact cleaner (`--dry-run` supported).
  - `scripts/maintenance/clean.ps1`: Native PowerShell cleanup script for Windows environments.
  - `scripts/maintenance/cache_cleaner.py`: Standalone CLI launcher for manual or cron-driven cache purging.
  - `scripts/audit/audit_footprint.py`: Single-pass disk usage and folder profiler identifying Top 10 space consumers.
  - `scripts/audit/audit_footprint.ps1`: PowerShell wrapper for disk footprint inspection.
  - `scripts/audit/test_email.py`: Visual verification tool dispatching sample HTML cards across all intake templates.

#### 9. Top-Level Entry Points
- **`main.py`**: Central CLI entry point for spontaneous harvests, batch jobs (`--all`), scheduler execution (`--scheduler`), cache flushes (`--clear-cache`), and test execution (`--test`).
- **`run.py`**: Non-interactive command-line runner wrapper.
- **`scheduler.py`**: Persistent 3-tier IST reminder daemon and IMAP polling loop.
- **`drive_sync.py`**: Standalone Drive upload test utility and one-time OAuth 2.0 browser authorization runner (`python drive_sync.py --login`).

---

### 2.3 Migration & Backward-Compatibility Guide

To ensure zero downtime and prevent broken command-line aliases, the consolidation introduced backward-compatibility shims at the project root:

| Previous Root Location | New Modular Location | Backward Compatibility Status | Recommended New Import / CLI Invocation |
|:---|:---|:---|:---|
| `analyzer.py` | `core/analyzer.py` | ✅ Root shim re-exports `core.analyzer` | `from core.analyzer import PaperAnalyzer` |
| `batch_runner.py` | `core/batch_runner.py` | ✅ Root shim re-exports `core.batch_runner` | `from core.batch_runner import ResilientBatchRunner` |
| `database.py` | `core/database.py` | ✅ Root shim re-exports `core.database` | `from core.database import DatabaseManager, db` |
| `csv_builder.py` | `utils/csv_builder.py` | ✅ Root shim re-exports `utils.csv_builder` | `from utils.csv_builder import StandardizedCsvBuilder` |
| `excel_builder.py` | `utils/excel_builder.py` | ✅ Root shim re-exports `utils.excel_builder` | `from utils.excel_builder import StandardizedExcelBuilder` |
| `cache_cleaner.py` | `scripts/maintenance/cache_cleaner.py` | ✅ Root shim delegates to `services.cache.cleaner` | `python scripts/maintenance/cache_cleaner.py` |
| `clean.ps1` | `scripts/maintenance/clean.ps1` | ✅ Root wrapper launches `scripts/maintenance/clean.ps1` | `.\scripts\maintenance\clean.ps1` or `.\clean.ps1` |
| `clean.py` | `scripts/maintenance/clean.py` | ✅ `scripts/clean.py` wrapper delegates to maintenance | `python scripts/maintenance/clean.py` |
| `audit_footprint.py` | `scripts/audit/audit_footprint.py` | ✅ `scripts/audit_footprint.py` delegates to audit | `python scripts/audit/audit_footprint.py` |
| `test_email.py` | `scripts/audit/test_email.py` | ✅ Root shim delegates to `scripts.audit.test_email` | `python scripts/audit/test_email.py` |
| `output/` | `storage/output/` | ✅ `cfg.OUTPUT_DIR` resolves to `storage/output/` | Checked via `cfg.OUTPUT_DIR` |
| `cache/` | `storage/cache/` | ✅ `cfg.CACHE_DIR` resolves to `storage/cache/` | Checked via `cfg.CACHE_DIR` |
| `logs/` | `storage/logs/` | ✅ `cfg.LOGS_DIR` resolves to `storage/logs/` | Checked via `cfg.LOGS_DIR` |
| `temp/` | `storage/temp/` | ✅ `cfg.TEMP_DIR` resolves to `storage/temp/` | Checked via `cfg.TEMP_DIR` |
| `input/` | `storage/input/` | ✅ `cfg.INPUT_DIR` resolves to `storage/input/` | Checked via `cfg.INPUT_DIR` |

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
  1. Primary CSV output is written to: `storage/output/{run_name}.csv`.
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

## 5. ⚡ API Configuration, Token-Bucket Rate Limiting & Active Multi-Source Round-Robin Query Distributor

### Semantic Scholar Strict 1 req/sec Global Limiter
Semantic Scholar strictly penalizes rapid query bursts and concurrent queries with immediate `HTTP 429 Too Many Requests`. To completely eliminate uncontrolled concurrent bursts caused by unthrottled worker pools or `asyncio.gather()`, the pipeline routes all Semantic Scholar interactions through a process-wide singleton:
```python
# utils/rate_limiters.py
GLOBAL_SEMANTIC_SCHOLAR_LIMITER = TokenBucketRateLimiter(
    rate_limit_per_second=1.0,
    safety_buffer_seconds=0.05
)
```
Every endpoint call in [`SemanticScholarClient`](file:///c:/Users/rohan/Documents/##%20Code/5)%20October%20-%202026/The_Paper_Getter/services/academic/semantic_scholar.py) and [`SemanticScholarHarvester`](file:///c:/Users/rohan/Documents/##%20Code/5)%20October%20-%202026/The_Paper_Getter/harvester/semantic_scholar.py) awaits `GLOBAL_SEMANTIC_SCHOLAR_LIMITER.acquire_async()` or acquires the thread lock before sending outbound requests.

Credentials are read from `.env` via:
```bash
S2_API_KEY=s2k-vzrGP8XJrEi2kKHndpXUmiXTvpftTbF9izKpBWUL
```

#### Mathematical Rate Limiting & Token Bucket Formulation
The process-wide rate limiter enforces that for any two consecutive requests $R_i$ and $R_{i+1}$, the inter-request time delta satisfies:
$$\Delta t = t(R_{i+1}) - t(R_i) \ge \frac{1}{\text{rate}} + \delta_{\text{safety}}$$
With $\text{rate} = 1.0\text{ req/sec}$ and $\delta_{\text{safety}} = 0.05\text{s}$, the minimum interval is strictly:
$$\Delta t \ge 1.05\text{ seconds}$$

#### Active Query Distributor & Cross-Provider Round-Robin Rotation
Rather than treating secondary providers (OpenAlex, Crossref, arXiv, CORE) as emergency failovers triggered only after a circuit breaker trips, the pipeline implements an active query distributor ([`ActiveQueryDistributor`](file:///c:/Users/rohan/Documents/##%20Code/5)%20October%20-%202026/The_Paper_Getter/harvester/distributor.py)):
1. **Dynamic Provider Rotation:** Round-robins across all active academic repositories (`openalex`, `crossref`, `semantic_scholar`, `arxiv`, `core`).
2. **Elimination of Concurrent Bursts:** Sequential provider alternation replaces unthrottled concurrent bursts (`asyncio.gather`), ensuring every provider operates safely within polite rate constraints.
3. **Adaptive Deficit Pagination:** Rotates round-robin rounds, dynamically calculating `deficit = target_quota - len(papers)`, until the target verified quota is met or all remote catalogs are genuinely exhausted.

#### Dynamic Cooldown Buffer (5.5s) & Exponential Backoff Window
If any individual aggregator encounters remote rate throttling (HTTP 429), intermittent HTTP 5xx errors, or network socket timeouts:
1. **Immediate Aggregator Shift:** The distributor marks that provider as cooling down and immediately diverts incoming queries to alternative healthy aggregators (e.g., from Semantic Scholar to OpenAlex or Crossref) rather than hammering the throttling endpoint to exhaustion.
2. **Configurable Cooldown Buffer:** Cooldowns default to a baseline buffer:
   $$\tau_{\text{cooldown}} = 5.5\text{ seconds}$$
3. **Exponential Window Expansion:** Consecutive failures scale exponentially:
   $$\tau_{\text{backoff}} = \min\left(60.0, 5.5 \times 2^{\text{consecutive\_failures} - 1}\right)$$
4. **Auto-Recovery:** Once the cooldown window elapses, the distributor safely reinstates the aggregator into active round-robin rotation.

#### Multi-Provider Polite Pool & Rate Caps (OpenAlex, Crossref, arXiv, CORE)
- **OpenAlex REST API:** Operates at **10.0 requests per second** with CC0 registry metadata resolution and cursor-based deep pagination.
- **Crossref Works API:** Operates at up to **50.0 requests per second** by attaching polite pool headers: `User-Agent: AcademicHarvester/4.0 (mailto:{POLITE_EMAIL})`.
- **arXiv Atom XML:** Enforces a strict **3.10-second polite delay** between successive queries (`cfg.ARXIV_RATE_DELAY = 3.0`). Parses XML Atom feeds (`entry`, `title`, `published`, `link`) and extracts direct PDF URLs.
- **Semantic Scholar Graph API:** Process-wide **1.0 request per second** strict cumulative cap via `GLOBAL_SEMANTIC_SCHOLAR_LIMITER`.
- **CORE API v3:** Ingests open-access papers and research outputs via CORE's v3 search endpoints (`https://api.core.ac.uk/v3/search/works`).

---

## 6. 🌙 Automated Nightly Cache Invalidation, Compact Data Schema & Footprint Maintenance

### Midnight 00:00 IST Automated Purge Routine
At midnight Indian Standard Time (00:00 IST), the [`ThreeTierScheduler`](file:///c:/Users/rohan/Documents/##%20Code/5)%20October%20-%202026/The_Paper_Getter/scheduler.py) detects the date rollover:
1. Resets SQLite daily run state: `db.reset_daily_state_for_midnight(date_str)`.
2. Automatically executes [`purge_nightly_cache()`](file:///c:/Users/rohan/Documents/##%20Code/5)%20October%20-%202026/The_Paper_Getter/services/cache/cleaner.py).
3. Sweeps `cache/`, `temp/`, and `logs/` directories, unlinking transient artifacts older than 24 hours.

### Compact "Data-Only" Payload Schema
Raw API responses from aggregators often include 10–50 KB of extraneous provider metadata, nested JSON graphs, and unused contributor trees per paper. The cache layer permanently eliminates this storage waste by executing [`truncate_to_compact_payload()`](file:///c:/Users/rohan/Documents/##%20Code/5)%20October%20-%202026/The_Paper_Getter/services/cache/manager.py) before writing to disk:
```json
{
  "doi": "10.1109/tfuzz.2024.1234567",
  "title": "Adaptive Neuro-Fuzzy Inference Systems for Clinical Diagnosis",
  "year": 2024,
  "venue": "IEEE Transactions on Fuzzy Systems",
  "indexed_scopus": true,
  "indexed_wos": true,
  "open_access_url": "https://arxiv.org/pdf/2401.12345.pdf",
  "source": "OpenAlex",
  "verified_sources": ["Scopus", "Web of Science", "Crossref"],
  "cached_at": 1730200000.0
}
```
This reduces per-paper cache entry size by **85–92%** (from ~25 KB down to ~400 bytes), allowing tens of thousands of cached queries to occupy minimal disk space.

### LRU 30 MB Size-Capped Eviction Engine
To guarantee the project footprint never exceeds disk thresholds, [`CacheManager`](file:///c:/Users/rohan/Documents/##%20Code/5)%20October%20-%202026/The_Paper_Getter/services/cache/manager.py) enforces a strict size ceiling:
```python
MAX_CACHE_SIZE_MB = 30.0  # Defined in config/constants.py
```
Whenever the cache directory exceeds 30 MB, [`enforce_size_cap()`](file:///c:/Users/rohan/Documents/##%20Code/5)%20October%20-%202026/The_Paper_Getter/services/cache/manager.py) sorts all cached files by `st_mtime` (Least Recently Used) and evicts oldest entries until the total directory size drops below **24.0 MB (80% target safety watermark)**.

### Automated Disk Footprint Profiling (`audit_footprint.py` / `.ps1`)
To monitor disk usage and ensure the project remains lightweight:
```bash
# Python single-pass execution
python scripts/audit_footprint.py

# Or via PowerShell
.\scripts\audit_footprint.ps1
```
The audit scans the workspace in a single $O(N)$ pass, displaying:
- Top 10 largest subdirectories ranked by megabytes.
- Top 10 largest individual files.
- Categorized breakdown: Core Project Source Code, Virtual Environment (`.venv`), Git History (`.git`), Runtime Output (`storage/output/`), and Transient Cache (`storage/cache/`, `storage/temp/`).

### Zero-Dependency Safe Artifact Purger (`clean.py` / `clean.ps1`)
To safely wipe build artifacts, bytecode, test files, and stale logs without deleting virtual environments or user `.env` files:
```bash
# Dry run preview (no files removed)
python scripts/maintenance/clean.py --dry-run
# Or backward-compatible wrapper:
python scripts/clean.py --dry-run

# Live purge
python scripts/maintenance/clean.py
# Or backward-compatible wrapper:
python scripts/clean.py

# Native PowerShell utility
.\scripts\maintenance\clean.ps1 -DryRun
# Or root convenience launcher:
.\clean.ps1 -DryRun
.\clean.ps1
```
Items safely purged include:
- `__pycache__/` and `*.pyc` bytecode files.
- `storage/temp/`, `.pytest_cache/`, `.mypy_cache/`.
- Stale SQLite temporary files (`*.db-wal`, `*.db-shm`).
- Stale CSV/XLSX exports in `storage/output/` (optional `--include-output`).
- Dangling test artifact files (`test_*.csv`, `test_*.xlsx`).

---

## 7. ☁️ Google Drive Cloud Storage & 403 Storage Quota Resolution

### Root Cause of the 403 Storage Quota Error
When uploading files to Google Drive with standard service account keys, developers encounter:
```text
HttpError 403: "The user's Drive storage quota has been exceeded."
"reason": "storageQuotaExceeded"
```

#### 🧠 The Technical Explanation:
- A Google Cloud **Service Account** (a bot account ending in `@...iam.gserviceaccount.com`) is provisioned by Google with **exactly 0 bytes (0 KB)** of Google Drive storage space.
- Even if you create a folder on your personal Google Drive (`@gmail.com`) and share it with the service account bot email as an Editor, whenever the bot uploads a file, Google assigns **file ownership to the service account**.
- Because the service account has a 0-byte quota, Google immediately blocks the upload with `storageQuotaExceeded (403)`.

---

### Architectural Solutions: Two Approved Methods

The pipeline supports two robust solutions depending on whether you are using a personal `@gmail.com` account or an organizational Google Workspace domain:

```
                                [Choose Your Google Drive Setup]
                                                │
                     ┌──────────────────────────┴──────────────────────────┐
                     ▼                                                     ▼
    [Method 1: Personal @gmail.com Drive]                 [Method 2: Google Workspace Domain]
     • Switch to User OAuth 2.0                            • Keep Service Account JSON
     • Place 'credentials.json' in root                    • Target Google Workspace Shared Drive
     • First run generates 'token.json'                    • Add Service Account as Content Manager
     • Uses your 15 GB+ personal quota 🚀                  • Files consume organizational pool
```

---

### 📘 Method 1: The Complete Dummy-Proof Setup Guide (Personal @gmail.com Drives - Recommended)

*Best for researchers and developers using standard personal Google accounts.*

Instead of pretending to be a bot with 0 storage, we switch your pipeline to **OAuth 2.0 (User Credentials)**. This tells Google: *"Hey, this script is uploading on behalf of my personal Google account."* Your personal Google Drive has 15 GB+ of space, so files upload smoothly without quota issues!

#### 📍 Phase 1: Configure the Google Cloud Consent Screen
1. Open your browser and go to [Google Cloud Console](https://console.cloud.google.com/).
2. In the top bar, ensure your project (e.g., `Paper-Harvester-Drive`) is selected.
3. Open the left sidebar menu (`☰` in the top left) and go to:
   👉 **APIs & Services** $\rightarrow$ **OAuth consent screen** (or **Google Auth Platform**).
4. **Select Audience / User Type:**
   - Choose **External** (allows you to test with your personal Gmail address).
   - Click **Create** / **Next**.
5. **Fill in App Information:**
   - **App name:** `Paper getter`
   - **User support email:** Select your Gmail from the dropdown.
   - **Developer contact email:** Type your personal Gmail address.
   - Click **Save and Continue**.
6. **Scopes (Permissions):**
   - Click **Add or Remove Scopes**.
   - In the filter box, search for `drive.file`.
   - Check the box for:
     `https://www.googleapis.com/auth/drive.file` (*See, edit, create, and delete only the specific Google Drive files you use with this app*).
   - Click **Update**, then **Save and Continue**.
7. **Test Users (⚠️ CRITICAL STEP — DO NOT SKIP):**
   - Since your app is in "Testing" mode, Google blocks everyone by default.
   - Click **+ Add Users**.
   - Type your exact personal Google email address (the one whose Drive you want to upload to).
   - Click **Add**, then **Save and Continue**.
   - Click **Back to Dashboard**.

#### 📍 Phase 2: Create and Download `credentials.json`
1. Go to the left sidebar menu and click **Credentials** (or **Clients**).
2. Click the blue **`+ Create Credentials`** button at the top and select **OAuth client ID**.
3. In the setup form:
   - **Application type:** Select **Desktop app**.
   - **Name:** `Paper getter`
   - Click **Create**.
4. Once created, click on `Paper getter` to open its details.
5. In the **Client secrets** section at the bottom right:
   - Click the **Download icon** (the arrow pointing down into a tray).
6. **Rename and place the file:**
   - Rename the downloaded JSON file to exactly:
     ```text
     credentials.json
     ```
   - Move `credentials.json` directly into your project's root folder (`The_Paper_Getter`).

#### 📍 Phase 3: Install Required Python Packages
Ensure the required Google OAuth and API client libraries are installed in your virtual environment:
```bash
pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

#### 📍 Phase 4: How Authentication Works in the Code
[`services/drive/oauth.py`](file:///c:/Users/rohan/Documents/##%20Code/5)%20October%20-%202026/The_Paper_Getter/services/drive/oauth.py) and [`services/drive/client.py`](file:///c:/Users/rohan/Documents/##%20Code/5)%20October%20-%202026/The_Paper_Getter/services/drive/client.py) automate authentication:
1. **On First Run:** If `token.json` is missing, running `python drive_sync.py` or the pipeline automatically launches your default browser for a one-time Google Account approval.
2. **Token Storage:** Once approved, the access and refresh tokens are persisted to `token.json` in the project root.
3. **Subsequent Runs:** The client loads `token.json` and automatically refreshes tokens in the background without opening the browser again!

#### 🚀 What Happens on Your First Run?
When you authenticate for the first time:
1. **A browser tab will automatically pop open** asking you to choose your Google Account.
2. **Select the Gmail address** you added as a **Test User** in Phase 1.
3. **Google Security Warning Screen:**
   - You will see: *"Google hasn't verified this app"*.
   - **Do not panic!** This is standard for private developer projects.
   - Click **Advanced** (small link in the lower left).
   - Click **Go to Paper getter (unsafe)**.
4. Click **Continue** to grant the app permission to upload files to your Drive.
5. The browser will confirm: *"The authentication flow has completed. You may close this window."*
6. The script creates **`token.json`** in your project folder, and all future uploads use your personal 15 GB quota!

#### 🔒 Important Git Security Rule
To ensure you never accidentally leak client secrets or access tokens to GitHub, ensure your [`.gitignore`](file:///c:/Users/rohan/Documents/##%20Code/5)%20October%20-%202026/The_Paper_Getter/.gitignore) contains:
```gitignore
credentials.json
credentials*.json
Credential.json
Credential*.json
token.json
Token.json
.env
```

---

### Method 2: Google Workspace Shared Drive (Team Drive)
*Best for universities, enterprises, and research labs with Google Workspace accounts.*

In a Google Workspace Shared Drive, files belong to the **domain pool** rather than an individual user's personal quota.
1. Create or open the Shared Drive in Google Drive.
2. Click **Manage Members** and add your service account email (`your-service-account@project.iam.gserviceaccount.com`) as a **Content Manager** or **Contributor**.
3. Copy the Shared Drive ID from the browser URL (or the specific folder ID inside the Shared Drive) and set them in `.env`:
   ```bash
   GDRIVE_SHARED_DRIVE_ID=0AFxxx...
   GDRIVE_FOLDER_ID=1A2B3C...
   GDRIVE_SERVICE_ACCOUNT_JSON=service_account.json
   ```
4. All Google Drive API v3 calls automatically pass `supportsAllDrives=True` and `corpora='drive'`.

---

### Pre-Flight Validation Logging & Storage Mode Detection
To prevent mid-pipeline crashes, [`GoogleDriveClient`](file:///c:/Users/rohan/Documents/##%20Code/5)%20October%20-%202026/The_Paper_Getter/services/drive/client.py) executes pre-flight validation via [`validate_upload_quota_preconditions()`](file:///c:/Users/rohan/Documents/##%20Code/5)%20October%20-%202026/The_Paper_Getter/services/drive/quota.py) prior to attempting file streaming:
1. Detects whether auth is running in **User OAuth 2.0 Mode** (`token.json` / `credentials.json`) or **Service Account Mode** (`service_account.json`).
2. If running in User OAuth 2.0 mode: logs `🔐 Auth Mode: USER_OAUTH_2.0 (Personal Drive storage space utilized)` and proceeds safely.
3. If running in Service Account mode against a personal `My Drive` folder without Shared Drive backing, logs an actionable warning explaining the 403 quota constraint and recommends User OAuth 2.0.

### Payload Size Tracking & Resumable Chunked Streaming
- **Target Size Range:** Harvested paper exports typically range between 5 KB and 400 KB.
- **Resumable Streaming:** Uses `MediaFileUpload(resumable=True, chunksize=1024*1024)` to stream CSV and XLSX datasets safely even over unstable network connections.
- **Optional Gzip Compression:** Enabling `GDRIVE_ENABLE_GZIP=true` compresses `.csv` files into `.csv.gz`, achieving an 80–90% reduction in transport payload size.

---

## 8. 📋 Formatted Two-Tier CSV Architecture & 32-Field Analytical Dataset

Output files generated by [`StandardizedCsvBuilder`](file:///c:/Users/rohan/Documents/##%20Code/5)%20October%20-%202026/The_Paper_Getter/csv_builder.py) follow a standardized **two-tier template layout** engineered for immediate human readability in spreadsheet viewers (Excel, Google Sheets) while remaining fully parseable by automated data pipelines (Pandas, Polars, R).

```
┌───────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ TIER 1: RUN METADATA HEADER BLOCK (Rows 1 to 15)                                                      │
├──────────┬─────────────────────────────┬──────────────────────────┬──────────┬────────────────────────┤
│ Column A │ Columns B & C               │ Column D                 │ Column E │ Column F               │
│ (Spacer) │ Primary Execution Metrics   │ (Blank Separator)        │ Key      │ Secondary Analytics    │
├──────────┼─────────────────────────────┼──────────────────────────┼──────────┼────────────────────────┤
│ (Blank)  │ Query String                │ (Blank)                  │ Scopus/WoS Verified Count         │
│ (Blank)  │ Total Papers Harvested      │ (Blank)                  │ Open Access Matches               │
│ (Blank)  │ Duplicates Dropped          │ (Blank)                  │ Aggregators Queried               │
│ (Blank)  │ Retained Verified Count     │ (Blank)                  │ Filter Mode                       │
│ (Blank)  │ Strict Mode Status          │ (Blank)                  │ Target Quota                      │
│ (Blank)  │ Timestamp                   │ (Blank)                  │ Institutional Credentials         │
│ (Blank)  │ Execution Duration          │ (Blank)                  │ Run Identifier                    │
│ (Blank)  │ Run Type                    │ (Blank)                  │ Excluded Non-Indexed              │
│ (Blank)  │ Location                    │ (Blank)                  │ Relevance Average                 │
│ (Blank)  │ Document Filter             │ (Blank)                  │ Pipeline Version                  │
│ (Blank)  │ Year Range                  │ (Blank)                  │ Google Drive Link                 │
│ (Blank)  │ Rate Limiter Status         │ (Blank)                  │ Query Distributor                 │
│ (Blank)  │ Deduplication Mode          │ (Blank)                  │ Cache Maintenance                 │
│ (Blank)  │ CSV Specification           │ (Blank)                  │ Encoding                          │
├──────────┴─────────────────────────────┴──────────────────────────┴──────────┴────────────────────────┤
│ ROW 15: BLANK BUFFER ROW (Visual & Programmatic Boundary)                                            │
├───────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ TIER 2: TABULAR PAPER DATASET (Rows 16 to End)                                                        │
├──────────┬────────────────────────────────────────────────────────────────────────────────────────────┤
│ ROW 16   │ Column Headers: 32 Analytical Fields starting strictly at Column B                         │
│ ROW 17+  │ Paper Records: Populated verified citations starting strictly at Column B                  │
└──────────┴────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 32 Standard Analytical Fields Breakdown (Columns B through AG)

| Col | Field Name | Description | Example Value |
|---|---|---|---|
| **B** | `Material ID` | Unique dataset material code | `MAT-001` |
| **C** | `Title` | Sanitized publication title | `Adaptive Neuro-Fuzzy Inference Systems` |
| **D** | `Authors` | Semicolon-delimited author names | `Jang, J.-S. R.; Sun, C.-T.` |
| **E** | `Year` | 4-digit publication year | `2024` |
| **F** | `DOI` | Canonical lowercase DOI | `10.1109/21.256541` |
| **G** | `Venue` | Full journal or conference venue name | `IEEE Transactions on Fuzzy Systems` |
| **H** | `Publication Type` | Publication format category | `Journal Article` |
| **I** | `URL` | Web resolver URL | `https://doi.org/10.1109/21.256541` |
| **J** | `PDF Link` | Direct Open Access PDF link | `https://arxiv.org/pdf/2401.12345.pdf` |
| **K** | `Source` | Discovery engine name | `OpenAlex` |
| **L** | `Index Status` | Consolidated Scopus/WoS indexing status | `Scopus & WoS Indexed` |
| **M** | `Scopus Indexed` | Scopus verification boolean | `Y` |
| **N** | `WoS Indexed` | Web of Science verification boolean | `Y` |
| **O** | `IEEE Indexed` | IEEE Xplore verification boolean | `Y` |
| **P** | `Open Access Status` | Open Access status boolean | `Y` |
| **Q** | `Citation Count` | Remote citation count | `48` |
| **R** | `Verified Sources` | JSON array of validating aggregators | `["Scopus", "Web of Science", "Crossref"]` |
| **S** | `Abstract` | Sanitized multiline abstract text | `This study presents an adaptive architecture...` |
| **T** | `Main Research Problem` | Core research objective addressed | `Nonlinear system identification under uncertainty` |
| **U** | `Main Application` | Domain deployment area | `Biomedical EEG signal classification` |
| **V** | `Importance` | Analytical importance rating | `High` |
| **W** | `Learning Level` | Complexity rating | `Intermediate` |
| **X** | `Taxonomy` | Primary category classification code | `CAT-04` |
| **Y** | `Primary Category Name` | Primary taxonomy name | `Neuro-Fuzzy Learning & Tuning` |
| **Z** | `Secondary Category 1` | Cross-domain taxonomy 1 | `Type-2 Fuzzy Logic Systems` |
| **AA**| `Secondary Category 2` | Cross-domain taxonomy 2 | `Explainable AI & Rule Extraction` |
| **AB**| `Secondary Category 3` | Cross-domain taxonomy 3 | `Biomedical Applications` |
| **AC**| `Research Status` | Literature workflow status | `Identified` |
| **AD**| `Reading Status` | Reading review status | `Not Started` |
| **AE**| `Relevance Score` | Computed relevance rating (1-10) | `10` |
| **AF**| `Notes` | Internal researcher remarks | `Foundational citation for Section 3 methodology` |
| **AG**| `Date Added` | Dataset ingestion timestamp | `2026-10-29` |

### Excel, Google Sheets & Pandas Dual-Tier Compatibility
- **UTF-8 with BOM (`utf-8-sig`):** Prepends the 3-byte Byte Order Mark (`\xef\xbb\xbf`) so Excel on Windows renders Greek characters ($\alpha, \beta, \gamma$), mathematical symbols, and umlauts without encoding distortion.
- **RFC 4180 Escaping:** Quotes fields containing commas, line breaks, or quotation marks. Internal double quotes are escaped as `""`.
- **Automated Pandas Ingestion:** When ingesting into Pandas, users can pass `header=15` (0-indexed) or use the built-in parser in [`batch_runner.py`](file:///c:/Users/rohan/Documents/##%20Code/5)%20October%20-%202026/The_Paper_Getter/batch_runner.py), which automatically sniffs whether the file is single-tier or two-tier:
  ```python
  import pandas as pd
  df = pd.read_csv("storage/output/Run_Example.csv", skiprows=15).dropna(how="all", axis=1)
  ```

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
- **Symptom:** `HttpError 403: The user's Drive storage quota has been exceeded` (`storageQuotaExceeded`).
- **Root Cause:** A Google Cloud Service Account has **0 bytes personal storage quota**. Uploading directly into a folder on a personal Google account (`@gmail.com`) causes Google to assign file ownership to the service account, instantly failing quota checks.
- **Fail-Safe Recovery & Resolution:**
  1. **Method 1 (Personal Drive @gmail.com):** Switch to User OAuth 2.0 authentication by placing `credentials.json` in the root and letting `services/drive/oauth.py` generate `token.json`. Files uploaded will be owned by your personal account and use your personal Drive quota.
  2. **Method 2 (Workspace Domain):** Use a Google Workspace Shared Drive (Team Drive) where files consume the organizational domain storage pool rather than individual service account quotas (`supportsAllDrives=True`).
  3. **Pre-Flight Validation:** Pre-flight checks (`validate_drive_target_or_fail`) detect incompatible combinations before streaming, logging explicit guidance.
  4. **Fail-Safe Local Storage:** If Drive sync fails or is unconfigured, the exported two-tier CSV is safely preserved in `storage/output/` and attached directly to the completion email.

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

### Scenario F: Module Migration & Path Resolution After Structural Consolidation
- **Symptom:** `ModuleNotFoundError: No module named '...'` when executing scripts from nested subdirectories or running custom external scripts that imported top-level modules.
- **Root Cause:** Single-purpose scripts were consolidated into purpose-built directories (`core/`, `utils/`, `services/`, `scripts/maintenance/`, `scripts/audit/`).
- **Fail-Safe Recovery & Resolution:**
  1. **Root Backward-Compatibility Shims:** The root directory preserves seamless shims (`analyzer.py`, `batch_runner.py`, `database.py`, `csv_builder.py`, `excel_builder.py`, `cache_cleaner.py`, `test_email.py`, `clean.ps1`). Legacy imports `from analyzer import PaperAnalyzer` and `from csv_builder import StandardizedCsvBuilder` continue to work without modification.
  2. **Dynamic Root Keying (`BASE_DIR`):** All path lookups for `.env`, `credentials.json`, `token.json`, and database paths are dynamically resolved from `BASE_DIR = Path(__file__).resolve().parent...`. You can invoke scripts from any working directory (`python scripts/maintenance/clean.py` or from the repository root) without relative path breakage.
  3. **Storage Relocation:** If looking for outputs or cache dumps, locate them under `storage/output/` and `storage/cache/` (or query `cfg.OUTPUT_DIR` / `cfg.CACHE_DIR`).

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

# 8. Run automated unit test suite (59 comprehensive tests)
python -m unittest discover tests
# Or via main CLI:
python main.py --test

# 9. Profile workspace disk footprint (single-pass audit)
python scripts/audit/audit_footprint.py
# Or backward-compatible wrapper:
python scripts/audit_footprint.py
# Or native PowerShell wrapper:
.\scripts\audit\audit_footprint.ps1

# 10. Clean transient caches, bytecode, and temp artifacts safely
python scripts/maintenance/clean.py --dry-run   # Preview items to be deleted
python scripts/maintenance/clean.py             # Execute cleanup
# Or root convenience launcher:
.\clean.ps1 -DryRun
.\clean.ps1

# 11. Test visual HTML email cards and dispatches
python scripts/audit/test_email.py --all
# Or backward-compatible wrapper:
python test_email.py --all

# 12. Google Drive OAuth 2.0 user login flow (Method 1)
python drive_sync.py --login
```
