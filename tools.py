"""
tools.py — Tools the ESG Intelligence Agent can use.

Seven tools:
  1. web_search            — search ESG reports, construction news, regulations
  2. read_page             — read full content of a report / article / regulation
  3. lookup_carbon_factor  — query the embodied-carbon factor database
  4. estimate_embodied_carbon — run an automated A1-A3 LCA on a bill of materials
  5. load_history          — load previous run so the agent can track trends
  6. save_report           — write the markdown report, render a PDF, update history
"""

import os
import json
import glob
from datetime import date

import requests
from bs4 import BeautifulSoup

import carbon_data
import lca
from report import markdown_to_pdf
from config import REPORTS_DIR, DATA_DIR, HISTORY_FILE, USER_AGENT


# ──────────────────────────────────────────────────────────────────────────
# TOOL 1: Web search (Tavily)
# ──────────────────────────────────────────────────────────────────────────

def web_search(query: str, num_results: int = 8, focus: str = "general") -> str:
    """
    Search the web via Tavily for ESG / construction / regulation intelligence.
    `focus` ('regulation' | 'news' | 'esg_report' | 'carbon' | 'general')
    biases the query toward authoritative sources.
    """
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return json.dumps({"error": "TAVILY_API_KEY not set."})

    hints = {
        "regulation": " ESG regulation policy 2025 2026 (CSRD OR CBAM OR taxonomy OR disclosure)",
        "news": " construction sustainability news 2026",
        "esg_report": " ESG sustainability report disclosure",
        "carbon": " embodied carbon EPD building materials trend",
        "general": "",
    }
    full_query = f"{query}{hints.get(focus, '')}"

    try:
        resp = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": api_key,
                "query": full_query,
                "max_results": num_results,
                "search_depth": "advanced",
                "include_answer": True,
            },
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        out = {
            "answer": data.get("answer", ""),
            "results": [
                {"title": r.get("title", ""), "url": r.get("url", ""),
                 "snippet": r.get("content", "")[:500]}
                for r in data.get("results", [])
            ],
        }
        return json.dumps(out, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ──────────────────────────────────────────────────────────────────────────
# TOOL 2: Read a page
# ──────────────────────────────────────────────────────────────────────────

def read_page(url: str, max_chars: int = 4000) -> str:
    """Fetch and return cleaned text from a URL (report, article, or regulation)."""
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer", "aside", "form"]):
            tag.decompose()
        text = "\n".join(
            ln for ln in soup.get_text("\n", strip=True).splitlines() if ln.strip()
        )
        return text[:max_chars] + ("..." if len(text) > max_chars else "")
    except Exception as e:
        return f"Error reading page: {e}"


# ──────────────────────────────────────────────────────────────────────────
# TOOL 3: Carbon factor lookup
# ──────────────────────────────────────────────────────────────────────────

def lookup_carbon_factor(material: str = "", list_all: bool = False) -> str:
    """Look up the embodied carbon factor for a material, or list the catalogue."""
    if list_all or not material:
        return json.dumps(carbon_data.list_materials(), indent=2)
    key, rec = carbon_data.find_material(material)
    if not rec:
        return json.dumps({
            "found": False, "query": material,
            "hint": "No close match. Call lookup_carbon_factor with list_all=true to see the catalogue.",
        })
    out = {"found": True, "query": material, **rec}
    sub = carbon_data.SUBSTITUTIONS.get(key)
    if sub:
        sk, advice = sub
        out["lower_carbon_alternative"] = {
            "name": carbon_data.MATERIALS[sk]["name"],
            "factor_kgco2e_per_kg": carbon_data.MATERIALS[sk]["factor"],
            "advice": advice,
        }
    return json.dumps(out, indent=2)


# ──────────────────────────────────────────────────────────────────────────
# TOOL 4: Automated LCA
# ──────────────────────────────────────────────────────────────────────────

def estimate_embodied_carbon(bill_of_materials: str) -> str:
    """
    Run an automated cradle-to-gate (A1-A3) embodied-carbon estimate.
    `bill_of_materials` is a JSON array of {"material","quantity","unit"} objects.
    Units: kg, t, m3.
    """
    try:
        bom = json.loads(bill_of_materials) if isinstance(bill_of_materials, str) else bill_of_materials
        if isinstance(bom, dict) and "bill_of_materials" in bom:
            bom = bom["bill_of_materials"]
        if not isinstance(bom, list):
            return json.dumps({"error": "bill_of_materials must be a JSON array of objects."})
    except Exception as e:
        return json.dumps({"error": f"Could not parse bill_of_materials JSON: {e}"})

    result = lca.calculate(bom)
    return json.dumps(result, indent=2)


# ──────────────────────────────────────────────────────────────────────────
# TOOL 5: Load history
# ──────────────────────────────────────────────────────────────────────────

def load_history() -> str:
    """Load the previous run's tracked metrics so the agent can report trends."""
    if not os.path.exists(HISTORY_FILE):
        return json.dumps({
            "message": "No history found — this appears to be the first run.",
            "previous": {},
        })
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.dumps(json.load(f), indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Could not load history: {e}"})


# ──────────────────────────────────────────────────────────────────────────
# TOOL 6: Save the report (markdown + PDF + history)
# ──────────────────────────────────────────────────────────────────────────

def save_report(content: str, metrics: str = "{}") -> str:
    """
    Save the markdown report, render it to PDF, and update history.json.

    `metrics` is a JSON object of trackable numbers to compare next run, e.g.
    {"watched_regulations": 6, "key_material_factors": {"steel": 1.55},
     "headline": "EU CBAM definitive period tightens steel reporting"}.
    """
    os.makedirs(REPORTS_DIR, exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)
    today = date.today().isoformat()

    md_path = os.path.join(REPORTS_DIR, f"esg_brief_{today}.md")
    pdf_path = os.path.join(REPORTS_DIR, f"esg_brief_{today}.pdf")

    try:
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception as e:
        return f"Error saving markdown report: {e}"

    pdf_msg = ""
    try:
        if markdown_to_pdf(content, pdf_path):
            pdf_msg = f" PDF rendered: {pdf_path}."
        else:
            pdf_msg = " (PDF skipped — install 'reportlab' to enable PDF output.)"
    except Exception as e:
        pdf_msg = f" (PDF render failed: {e})"

    try:
        parsed = json.loads(metrics) if isinstance(metrics, str) else metrics
    except Exception:
        parsed = {"raw": metrics}
    history = {"date": today, "report_file": md_path, "metrics": parsed}
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except Exception as e:
        return f"Report saved to {md_path}, but failed to update history: {e}"

    return f"Report saved to {md_path}.{pdf_msg} History updated for tomorrow's comparison."


# ──────────────────────────────────────────────────────────────────────────
# Registry
# ──────────────────────────────────────────────────────────────────────────

TOOL_FUNCTIONS = {
    "web_search": web_search,
    "read_page": read_page,
    "lookup_carbon_factor": lookup_carbon_factor,
    "estimate_embodied_carbon": estimate_embodied_carbon,
    "load_history": load_history,
    "save_report": save_report,
}

TOOL_DEFINITIONS = [
    {
        "name": "web_search",
        "description": (
            "Search the web for ESG intelligence: ESG/sustainability reports, "
            "construction-sector news, and sustainability regulations. Set `focus` "
            "to 'regulation', 'news', 'esg_report', or 'carbon' to target authoritative "
            "sources. Returns a synthesised answer plus titles, URLs and snippets."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "num_results": {"type": "integer", "description": "Number of results (default 8)", "default": 8},
                "focus": {"type": "string", "enum": ["general", "regulation", "news", "esg_report", "carbon"],
                          "description": "Source bias", "default": "general"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "read_page",
        "description": "Read the full cleaned text of a URL — a regulation page, ESG report, or news article.",
        "input_schema": {
            "type": "object",
            "properties": {"url": {"type": "string", "description": "Full URL to read"}},
            "required": ["url"],
        },
    },
    {
        "name": "lookup_carbon_factor",
        "description": (
            "Look up the embodied carbon factor (kgCO2e/kg, cradle-to-gate A1-A3) for a "
            "construction material from the built-in database, including any lower-carbon "
            "alternative. Set list_all=true to retrieve the whole catalogue."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "material": {"type": "string", "description": "Material name, e.g. 'rebar', 'concrete C32/40', 'aluminium'"},
                "list_all": {"type": "boolean", "description": "Return the full catalogue", "default": False},
            },
        },
    },
    {
        "name": "estimate_embodied_carbon",
        "description": (
            "Run an automated cradle-to-gate (A1-A3) embodied-carbon estimate for a bill of "
            "materials. Returns total tCO2e, per-material breakdown, carbon hotspots, and "
            "circular-economy substitutions with quantified savings. Use this to demonstrate "
            "the '1clickLCA-style' automated assessment on any project example you find or invent."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "bill_of_materials": {
                    "type": "string",
                    "description": 'JSON array, e.g. [{"material":"concrete C32/40","quantity":120,"unit":"m3"},{"material":"rebar","quantity":9.5,"unit":"t"}]. Units: kg, t, m3.',
                },
            },
            "required": ["bill_of_materials"],
        },
    },
    {
        "name": "load_history",
        "description": "Load the previous run's tracked metrics so you can report what changed since last time. Call this FIRST.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "save_report",
        "description": (
            "Save the final markdown report, render it to a branded PDF, and update history.json "
            "for tomorrow's trend comparison. Pass the full markdown in `content` and a JSON object "
            "of trackable metrics in `metrics`."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "Full markdown report"},
                "metrics": {"type": "string", "description": "JSON object of numbers/headlines to track over time"},
            },
            "required": ["content"],
        },
    },
]
