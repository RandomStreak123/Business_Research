"""
Central configuration for the agent research backend.
Strictly configured for enterprise business research with docx-only output,
anti-hallucination parameters, and multi-threaded speed optimizations.
"""

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Auto-load .env if present
env_path = os.path.join(BASE_DIR, ".env")
if os.path.exists(env_path):
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("'\""))

# --- Provider (Groq: free tier, OpenAI-compatible) -------------------------
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_API_KEY_ENV_VAR = "GROQ_API_KEY"

# --- Model selection & fallback -------------------------------------------
PRIMARY_MODEL = os.environ.get("PRIMARY_MODEL", "openai/gpt-oss-120b")

FALLBACK_MODELS = [
    "openai/gpt-oss-20b",
    "qwen/qwen3.8-27b",
]

MAX_TOKENS = 3000

# Strict anti-hallucination sampling temperature (0.1 locks model to grounded retrieval)
LLM_TEMPERATURE = float(os.environ.get("LLM_TEMPERATURE", "0.1"))

# --- Retry / fallback behavior ---------------------------------------------
MAX_RETRIES_PER_MODEL = 2
RETRY_BACKOFF_SECONDS = 2

# --- Concurrency & Speed Optimization --------------------------------------
SEARCH_MAX_WORKERS = 4
EVALUATION_MAX_WORKERS = 3

# --- Report Specification --------------------------------------------------
MIN_REPORT_PAGES = 5
WORDS_PER_PAGE = 500
MIN_REPORT_WORDS = MIN_REPORT_PAGES * WORDS_PER_PAGE

# Output format: strictly Word document (.docx) only. No MD format supported.
DEFAULT_OUTPUT_FORMAT = "docx"

# --- Evaluation ------------------------------------------------------------
MAX_SECTION_REVISIONS = 1

# --- Project timeline caps -------------------------------------------------
DEFAULT_MAX_DAYS = 3

# --- Paths -----------------------------------------------------------------
REPORTS_DIR = os.path.join(BASE_DIR, "data", "reports")
LOGS_DIR = os.path.join(BASE_DIR, "data", "logs")

os.makedirs(REPORTS_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)