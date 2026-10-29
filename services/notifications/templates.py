"""
services/notifications/templates.py - HTML/Plain-text email templates & card layouts.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

from typing import Dict, Any, List, Optional
from config import cfg

BASE_EMAIL_FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
CODE_FONT = "'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, Courier, monospace"


def get_morning_questionnaire_template(date_str: str) -> str:
    """Returns plain-text template string for Morning Intake Questionnaire."""
    return f"""[NAME_OF_RUN]: Run_{date_str}_01
[RUN_TYPE]: Automated ⚙️ (Options: Automated | Manual | Batch)
[LOCATION]: HITS Campus 🏛️ (Options: HITS Campus | Home | Online VPS)
[BATCH_RUN]: No 📦 (Options: Yes | No)
[BATCH_DETAILS]: None 📑 (If Yes: specify batch file name and item position)
[OUTPUT_MODE]: Create New 📄 (Options: Create New | Append to Existing)
[TARGET_SHEET]: None 📊 (If Appending: name of target sheet/file)
[TOPIC_COUNT]: 2 🔢 (Max: 5)
[TOPIC_1]: Fuzzy Machine Learning
[T1_SUBTOPICS]: T-Norms, Type-2 Fuzzy Logic, Neuro-Fuzzy Systems, Fuzzy Clustering, Membership Tuning
[TOPIC_2]: Graph Neural Networks
[T2_SUBTOPICS]: Spectral Clustering, Link Prediction, Graph Attention Networks
[PAPERS_PER_TOPIC]: 250 📚 (Preset choices: 100 | 250 | 500 — Hard cap: 500)
[YEAR_RANGE]: 2021-2026 🗓️ (Format: YYYY-YYYY or 'All Years')
[DOC_TYPE]: Journal Articles Only 📑 (Options: Journal Articles Only | Conference Proceedings | Preprints | All)
[INST_TOKEN]: True 🔑 (Options: True [Scopus/WoS/IEEE authoritative] | False [Open Access fallback])
[TARGET_INDEX]: Scopus, Web of Science, IEEE Xplore, Crossref 🌐
[QUOTA_STRICTNESS]: Strict 🎯 (Options: Strict [paginate until filled] | Fast-Capped [stop on candidate limit])
"""


def wrap_html_container(title: str, header_gradient: str, header_icon: str, header_subtitle: str, content_html: str) -> str:
    """Wraps body content in a polished, responsive, card-based email layout."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
</head>
<body style="margin: 0; padding: 24px 12px; background-color: #f1f5f9; font-family: {BASE_EMAIL_FONT}; line-height: 1.6; color: #1e293b;">
    <div style="max-width: 660px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 14px rgba(0,0,0,0.06); border: 1px solid #e2e8f0;">
        <div style="background: {header_gradient}; color: #ffffff; padding: 28px 24px; text-align: left;">
            <div style="font-size: 24px; font-weight: 700; letter-spacing: -0.5px; margin: 0; display: flex; align-items: center;">
                <span>{header_icon} {title}</span>
            </div>
            <div style="font-size: 14px; opacity: 0.92; margin-top: 6px; font-weight: 400;">
                {header_subtitle}
            </div>
        </div>
        <div style="padding: 24px;">
            {content_html}
        </div>
        <div style="background-color: #f8fafc; border-top: 1px solid #e2e8f0; padding: 16px 24px; text-align: center; font-size: 12px; color: #64748b;">
            Academic Paper Harvester & Verifier • 100% Free Autonomous Research Automation Engine 🎓☕
        </div>
    </div>
</body>
</html>"""
