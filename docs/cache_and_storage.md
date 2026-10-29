# 💾 Cache Lifecycle & Cloud Storage Architecture

## Unified Academic Paper Harvester & Verifier

This document details the automated cache management lifecycle, nightly midnight purging routines, and Google Drive cloud storage synchronization patterns.

---

## 🧹 Cache Lifecycle & Automated Maintenance

```
 ┌────────────────────────────────────────────────────────────────────────┐
 │                      Nightly Midnight Purge (00:00 IST)                │
 ├────────────────────────────────┬───────────────────────────────────────┤
 │  Temporary Query Artifacts     │  Deleted if older than 24 hours       │
 │  API Response Dumps            │  Deleted if older than 24 hours       │
 │  Stale Verification Records    │  Deleted if older than 48 hours (TTL) │
 └────────────────────────────────┴───────────────────────────────────────┘
                                   ▲
                                   │ Triggered automatically by:
         ┌─────────────────────────┴────────────────────────┐
         │                                                  │
 ┌───────┴────────────────────────┐       ┌─────────────────┴───────────────────┐
 │ Background Scheduler Daemon    │       │ Cron / Command-Line Manual Override │
 │ (scheduler.py midnight reset)  │       │ (python main.py --clear-cache)      │
 └────────────────────────────────┘       └─────────────────────────────────────┘
```

### 1. Automated Nightly Cache Purging (00:00 IST)
At midnight Indian Standard Time (00:00 IST), the [`ThreeTierScheduler`](file:///c:/Users/rohan/Documents/##%20Code/5)%20October%20-%202026/The_Paper_Getter/scheduler.py) detects the date rollover:
1. Resets SQLite daily run state: `db.reset_daily_state_for_midnight(date_str)`.
2. Automatically executes [`purge_nightly_cache()`](file:///c:/Users/rohan/Documents/##%20Code/5)%20October%20-%202026/The_Paper_Getter/services/cache/cleaner.py).
3. Sweeps `cache/`, `temp/`, and `logs/` directories, permanently unlinking transient citation artifacts older than 24 hours. This guarantees that stale citation data does not persist into the following day's research intake.

### 2. Standalone Cron-Compatible Entrypoint
The maintenance routine can be invoked directly by external task runners (e.g., Linux `cron` or Windows Task Scheduler):
```bash
# Nightly sweep (evicts artifacts > 24 hours)
python -m services.cache.cleaner

# Complete cache flush (flushes all cached records on demand)
python -m services.cache.cleaner --clear-all
```

### 3. Manual CLI Override Flags
Users can flush the entire cache directory on demand using either `--clear-cache` or `--clean-cache`:
```bash
python main.py --clear-cache
```

---

## ☁️ Google Drive Sync & Storage Configuration

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

#### Option C: User-Level OAuth 2.0 Refresh Token
Switch from service account authentication to standard user-level OAuth 2.0:
```bash
GDRIVE_REFRESH_TOKEN=1//04xxx...
GDRIVE_CLIENT_ID=xxx.apps.googleusercontent.com
GDRIVE_CLIENT_SECRET=GOCSPX-xxx...
```

---

### Payload Optimization & Streaming
- **Target Size Range:** Harvested paper exports typically range between 5 KB and 400 KB.
- **Chunked Resumable Upload:** The pipeline uses `MediaFileUpload(resumable=True)` to stream files cleanly.
- **Optional Gzip Compression:** When remote transport bandwidth is constrained, enabling `GDRIVE_ENABLE_GZIP=true` compresses `.csv` files into `.csv.gz`, achieving an 80–90% reduction in transfer payload size.
