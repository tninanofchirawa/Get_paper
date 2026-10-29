"""
services/notifications/tag_parser.py - Inbound email questionnaire tag parsing & validation.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

import re
import datetime
from datetime import timezone, timedelta
from typing import Dict, Any, List, Tuple, Optional


def get_ist_now() -> datetime.datetime:
    """Returns the current datetime in Indian Standard Time (IST, UTC+5:30)."""
    ist_tz = timezone(timedelta(hours=5, minutes=30))
    return datetime.datetime.now(ist_tz)


TAG_REGEX_PATTERN = re.compile(
    r"\[(?P<tag>[A-Z0-9_]+)\][ \t]*[:=\-]?[ \t]*(?P<val>.*?)(?=[ \t]*\|[ \t]*\[|\r|\n|$)",
    re.IGNORECASE
)


def clean_field_value(raw_val: str) -> str:
    """Cleans user entered values from email templates."""
    if not raw_val:
        return ""
    v = raw_val.strip()
    v = re.sub(r"^[>\s]+", "", v).strip()
    v = re.sub(r"\s*\([^)]*(?:Options|Preset|Format|Max|If Yes|If Appending)[^)]*\)", "", v, flags=re.IGNORECASE).strip()
    v = re.sub(r"[\U00010000-\U0010ffff\u2600-\u26ff\u2700-\u27bf\ufe0f]", "", v).strip()
    return v


def parse_run_config_tags(body: str) -> Tuple[Optional[Dict[str, Any]], List[str]]:
    """
    Parses configuration tags from an incoming email reply body.
    Supports standard multi-line 15-tag template and single-line quick triggers.
    Enforces boundary conditions (Max 5 topics, Max 5 subtopics, Max 500 papers).
    Returns: (parsed_config_dict, error_list)
    """
    errors: List[str] = []
    tags: Dict[str, str] = {}

    for match in TAG_REGEX_PATTERN.finditer(body):
        tag_name = match.group("tag").strip().upper()
        raw_val = match.group("val")
        cleaned_val = clean_field_value(raw_val)
        if tag_name not in tags or cleaned_val:
            tags[tag_name] = cleaned_val

    if not tags:
        return None, ["No configuration tags (e.g., [NAME_OF_RUN], [TOPIC_1]) were detected in your email body."]

    if "TOPIC" in tags and "TOPIC_1" not in tags:
        tags["TOPIC_1"] = tags["TOPIC"]
    if "QUOTA" in tags and "PAPERS_PER_TOPIC" not in tags:
        tags["PAPERS_PER_TOPIC"] = tags["QUOTA"]

    date_str = get_ist_now().strftime("%Y%m%d")
    run_name = tags.get("NAME_OF_RUN") or f"Run_{date_str}_01"
    run_type = tags.get("RUN_TYPE") or "Automated"
    location = tags.get("LOCATION") or "Home"

    batch_str = tags.get("BATCH_RUN", "No").lower()
    is_batch = batch_str in ("yes", "y", "true", "1")
    batch_details = tags.get("BATCH_DETAILS") or "None"

    output_mode = tags.get("OUTPUT_MODE") or "Create New"
    target_sheet = tags.get("TARGET_SHEET") or "None"

    topics: List[str] = []
    subtopics_map: Dict[str, List[str]] = {}
    max_topics = 5

    if "TOPIC_COUNT" in tags and tags["TOPIC_COUNT"]:
        try:
            req_top_count = int(re.sub(r"[^\d]", "", tags["TOPIC_COUNT"]))
            if req_top_count > 5:
                errors.append(f"❌ [TOPIC_COUNT]: You requested {req_top_count} topics. (Maximum allowed is 5).")
            elif req_top_count > 0:
                max_topics = req_top_count
        except Exception:
            pass

    for i in range(1, 8):
        top_val = tags.get(f"TOPIC_{i}", "").strip()
        if top_val and top_val.lower() not in ("none", "null", "n/a", "-", ""):
            if i > 5:
                errors.append(f"❌ [TOPIC_{i}]: Topic '{top_val}' exceeds the maximum allowed limit of 5 topics.")
                continue

            if len(topics) < max_topics:
                topics.append(top_val)
                sub_raw = tags.get(f"T{i}_SUBTOPICS", "").strip()
                if sub_raw and sub_raw.lower() not in ("none", "null", "n/a", "-", ""):
                    subs = [s.strip() for s in re.split(r"[,;]+", sub_raw) if s.strip()]
                    if len(subs) > 5:
                        errors.append(f"❌ [T{i}_SUBTOPICS]: You provided {len(subs)} subtopics. (Maximum allowed is 5).")
                    subtopics_map[top_val] = subs[:5]
                else:
                    subtopics_map[top_val] = []

    if not is_batch and not topics:
        errors.append("❌ [TOPIC_1]: At least one topic must be specified.")

    quota_raw = tags.get("PAPERS_PER_TOPIC", "250").strip()
    quota = 250
    if quota_raw:
        try:
            num_match = re.search(r"\d+", quota_raw)
            if num_match:
                req_quota = int(num_match.group(0))
                if req_quota > 500:
                    errors.append(
                        f"❌ [PAPERS_PER_TOPIC]: You requested {req_quota} papers. "
                        f"(The hard ceiling is 500 papers per topic to prevent API blocks)."
                    )
                    quota = 500
                elif req_quota < 1:
                    quota = 250
                else:
                    quota = req_quota
        except Exception:
            quota = 250

    year_range = tags.get("YEAR_RANGE") or "All Years"
    doc_type = tags.get("DOC_TYPE") or "Journal Articles Only"

    inst_token_str = tags.get("INST_TOKEN", "True").lower()
    inst_token = inst_token_str in ("true", "yes", "y", "1")

    target_idx_raw = tags.get("TARGET_INDEX") or "Scopus, Web of Science, IEEE Xplore, Crossref"
    target_repos = [r.strip() for r in re.split(r"[,;]+", target_idx_raw) if r.strip()]

    quota_strictness = tags.get("QUOTA_STRICTNESS") or "Strict"
    if "fast" in quota_strictness.lower() or "capped" in quota_strictness.lower():
        quota_strictness = "Fast-Capped"
    else:
        quota_strictness = "Strict"

    only_idx_str = tags.get("ONLY_INDEXED") or tags.get("INDEXED_ONLY") or tags.get("STRICT_INDEXING") or "False"
    only_indexed = only_idx_str.lower() in ("true", "yes", "y", "1")

    if errors:
        return None, errors

    config = {
        "run_name": run_name,
        "run_type": run_type,
        "location": location,
        "is_batch": is_batch,
        "batch_details": batch_details,
        "output_mode": output_mode,
        "target_sheet": target_sheet,
        "topic_count": len(topics),
        "topics": topics,
        "subtopics_map": subtopics_map,
        "main_topic": topics[0] if topics else "Batch Run",
        "subtopics": subtopics_map.get(topics[0], []) if topics else [],
        "harvest_quota": quota,
        "year_range": year_range,
        "doc_filter": doc_type,
        "inst_token_flag": inst_token,
        "target_repos": target_repos,
        "quota_strictness": quota_strictness,
        "only_indexed": only_indexed,
    }
    return config, []
