"""
config.py - Central configuration for the ESG Intelligence Agent.
Override any of these with environment variables (e.g. in a .env file).
"""

import os

# Load a local .env file if python-dotenv is installed (optional convenience).
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ---- OpenAI (primary agent model) ----
# gpt-4o is the default (fast + capable, strong tool-calling).
# Override with ESG_MODEL=gpt-4o-mini for cheaper runs.
MODEL = os.getenv("ESG_MODEL", "gpt-4o")
MAX_TOKENS = int(os.getenv("ESG_MAX_TOKENS", "6000"))
MAX_STEPS = int(os.getenv("ESG_MAX_STEPS", "30"))

# ---- OpenAI API ----
# Set OPENAI_API_KEY in .env or as a GitHub Actions secret to enable.
OPENAI_MODEL = os.getenv("ESG_OPENAI_MODEL", "gpt-4o")
OPENAI_ENABLED = bool(os.getenv("OPENAI_API_KEY"))

# ---- Market / regulatory focus ----
# Drives which regulations and news the agent prioritises.
FOCUS_REGION = os.getenv("ESG_FOCUS_REGION", "Kazakhstan + global")

# ---- Paths ----
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPORTS_DIR = os.getenv("ESG_REPORTS_DIR", os.path.join(BASE_DIR, "reports"))
DATA_DIR = os.getenv("ESG_DATA_DIR", os.path.join(BASE_DIR, "data"))
HISTORY_FILE = os.path.join(DATA_DIR, "history.json")

# ---- HTTP ----
USER_AGENT = "Mozilla/5.0 (esg-intelligence-agent/1.0; +https://github.com/yenlikgaisina)"
