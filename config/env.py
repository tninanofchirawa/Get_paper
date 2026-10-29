"""
config/env.py - Environment variable loading and credential resolution.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

import os
from pathlib import Path
from typing import Optional


def load_env_file(env_path: Optional[str] = None):
    """Loads environment variables from .env file into os.environ if present."""
    base_dir = Path(__file__).resolve().parent.parent
    candidate_paths = [
        env_path,
        ".env",
        str(base_dir / ".env"),
        os.path.join(os.path.dirname(__file__), "..", ".env"),
    ]
    for p in candidate_paths:
        if p and os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k = k.strip()
                            v = v.strip().strip("'\"")
                            if k and k not in os.environ:
                                os.environ[k] = v
            except Exception:
                pass
            break


# Pre-load environment variables upon module import
load_env_file()
