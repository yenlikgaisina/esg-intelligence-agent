"""
tools.py — Tools the ESG Intelligence Agent can use.

Seven tools:
  1. web_search             — search ESG reports, construction news, regulations
    2. read_page              — read full content of a report / article / regulation
      3. lookup_carbon_factor   — query the embodied-carbon factor database
        4. estimate_embodied_carbon — run an automated A1-A3 LCA on a bill of materials
          5. load_history           — load previous run so the agent can track trends
            6. save_report            — write the markdown report, render a PDF, update history
              7. openai_analysis        — cross-check LCA results or regulatory text with GPT-4o
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
from config import REPORTS_DIR, DATA_DIR, HISTORY_FILE, USER_AGENT, OPENAI_MODEL, OPENAI_ENABLED

# ──────────────────────────────────────────────────────────────────────────
# TOOL 1: Web search (Tavily)
# ──────────────────────────────────────────────────────────────────────────

def web_search(query: str, max_results: int = 5) -> str:
      """Search the web for ESG / construction / regulatory content."""
      api_key = os.getenv("TAVILY_API_KEY")
      if not api_key:
                return "TAVILY_API_KEY not set — web search unavailable."
            try:
                      resp = requests.post(
                                    "https://api.tavily.com/search",
                                    json={"api_key": api_key, "query": query, "max_results": max_results,
                                                            "search_depth": "advanced", "include_answer": True},
                                    timeout=30,
                      )
                      resp.raise_for_status()
                      data = resp.json()
                      lines = []
                      if data.get("answer"):
                                    lines.append(f"Summary: {data['answer']}\n")
                                for r in data.get("results", []):
                                              lines.append(f"- [{r['title']}]({r['url']})\n  {r.get('content','')[:300]}")
                                          return "\n".join(lines) if lines else "No results."
except Exception as e:
        return f"Search error: {e}"


# ──────────────────────────────────────────────────────────────────────────
# TOOL 2: Read a web page
# ──────────────────────────────────────────────────────────────────────────

def read_page(url: str) -> str:
      """Fetch and return the plain-text content of a web page (max 8 000 chars)."""
    try:
              r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=20)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
                      tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        return text[:8000]
except Exception as e:
        return f"Error reading {url}: {e}"


# ──────────────────────────────────────────────────────────────────────────
# TOOL 3: Look up a single carbon factor
# ──────────────────────────────────────────────────────────────────────────

def lookup_carbon_factor(material: str) -> str:
      """Return the embodied-carbon factor (kgCO2e/unit) for a named material."""
    result = carbon_data.lookup(material)
    if result:
              return (
                            f"Material: {result['name']}\n"
                            f"Factor:   {result['factor_kgco2e_per_unit']} kgCO2e/{result['unit']}\n"
                            f"Source:   {result['source']}\n"
                            f"Notes:    {result.get('notes', '—')}"
              )
    return f"No carbon factor found for '{material}'. Try a broader term."


# ──────────────────────────────────────────────────────────────────────────
# TOOL 4: Estimate embodied carbon for a bill of materials
# ──────────────────────────────────────────────────────────────────────────

def estimate_embodied_carbon(materials_json: str) -> str:
      """
          Run a cradle-to-gate (A1-A3) LCA on a bill of materials.

              materials_json: JSON array of {"material": str, "quantity": float, "unit": str}
                  Returns a formatted report with total tCO2e, hotspots, and lower-carbon swaps.
                      """
    try:
              items = json.loads(materials_json)
except json.JSONDecodeError as e:
        return f"Invalid JSON: {e}"
    return lca.run(items)


# ──────────────────────────────────────────────────────────────────────────
# TOOL 5: Load run history
# ──────────────────────────────────────────────────────────────────────────

def load_history(n_last: int = 5) -> str:
      """Load the last N briefing summaries so the agent can spot trends."""
    if not os.path.exists(HISTORY_FILE):
              return "No history yet — this is the first run."
    try:
              with open(HISTORY_FILE, encoding="utf-8") as f:
                            history = json.load(f)
                        entries = history[-n_last:]
        lines = [f"=== Last {len(entries)} runs ==="]
        for e in entries:
                      lines.append(
                          f"\n{e.get('date','?')} | {e.get('headline','(no headline)')}\n"
                          f"  Top material: {e.get('top_material','?')} | "
                          f"Total tCO2e: {e.get('total_tco2e','?')}"
        )
        return "\n".join(lines)
except Exception as ex:
        return f"Error loading history: {ex}"


# ──────────────────────────────────────────────────────────────────────────
# TOOL 6: Save the report
# ──────────────────────────────────────────────────────────────────────────

def save_report(markdown: str, metrics_json: str = "{}") -> str:
      """
          Save today's briefing as markdown + PDF, and append a summary to history.

              markdown:     full markdown text of the briefing
                  metrics_json: JSON string with keys: headline, top_material, total_tco2e
                      """
    os.makedirs(REPORTS_DIR, exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)

    today = date.today().isoformat()
    md_path = os.path.join(REPORTS_DIR, f"esg_brief_{today}.md")
    pdf_path = os.path.join(REPORTS_DIR, f"esg_brief_{today}.pdf")

    with open(md_path, "w", encoding="utf-8") as f:
              f.write(markdown)

    pdf_result = markdown_to_pdf(markdown, pdf_path)

    # Update history
    try:
              metrics = json.loads(metrics_json)
except Exception:
        metrics = {}

    history = []
    if os.path.exists(HISTORY_FILE):
              with open(HISTORY_FILE, encoding="utf-8") as f:
                            try:
                                              history = json.load(f)
except Exception:
                history = []

    history.append({
              "date": today,
              "headline": metrics.get("headline", ""),
              "top_material": metrics.get("top_material", ""),
              "total_tco2e": metrics.get("total_tco2e", ""),
    })

    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
              json.dump(history, f, indent=2)

    return (
              f"Report saved:\n  Markdown: {md_path}\n  PDF: {pdf_result}\n"
              f"  History entries: {len(history)}"
    )


# ──────────────────────────────────────────────────────────────────────────
# TOOL 7: OpenAI cross-check analysis
# ──────────────────────────────────────────────────────────────────────────

def openai_analysis(prompt: str, context: str = "") -> str:
      """
          Send a prompt (+ optional context) to GPT-4o for a second-opinion analysis.

              Use cases:
                    - Cross-check an LCA result: did Claude miss anything?
                          - Summarise a dense regulatory text (e.g. EU CBAM implementing act)
                                - Get an alternative framing of carbon-reduction recommendations

                                    Returns GPT-4o's response as plain text, or a clear error if the key is missing.
                                        """
    if not OPENAI_ENABLED:
              return "OpenAI cross-check skipped — OPENAI_API_KEY not set."

    api_key = os.getenv("OPENAI_API_KEY")
    messages = []
    if context:
              messages.append({"role": "system", "content": context})
    messages.append({"role": "user", "content": prompt})

    try:
              resp = requests.post(
                            "https://api.openai.com/v1/chat/completions",
                            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                            json={"model": OPENAI_MODEL, "messages": messages, "max_tokens": 1500, "temperature": 0.3},
                            timeout=60,
              )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
except requests.HTTPError as e:
        return f"OpenAI API error {e.response.status_code}: {e.response.text[:300]}"
except Exception as e:
        return f"OpenAI call failed: {e}"


# ──────────────────────────────────────────────────────────────────────────
# Tool registry — used by agent.py
# ──────────────────────────────────────────────────────────────────────────

TOOL_FUNCTIONS = {
      "web_search": web_search,
      "read_page": read_page,
      "lookup_carbon_factor": lookup_carbon_factor,
      "estimate_embodied_carbon": estimate_embodied_carbon,
      "load_history": load_history,
      "save_report": save_report,
      "openai_analysis": openai_analysis,
}

TOOL_DEFINITIONS = [
      {
                "name": "web_search",
                "description": "Search the web for ESG reports, construction news, sustainability regulations, and embodied-carbon research.",
                "input_schema": {
                              "type": "object",
                              "properties": {
                                                "query": {"type": "string", "description": "Search query"},
                                                "max_results": {"type": "integer", "description": "Number of results (default 5)", "default": 5},
                              },
                              "required": ["query"],
                },
      },
      {
                "name": "read_page",
                "description": "Fetch and read the full text of a web page (report, article, regulation).",
                "input_schema": {
                              "type": "object",
                              "properties": {"url": {"type": "string", "description": "URL to fetch"}},
                              "required": ["url"],
                },
      },
      {
                "name": "lookup_carbon_factor",
                "description": "Look up the embodied-carbon emission factor for a specific construction material.",
                "input_schema": {
                              "type": "object",
                              "properties": {"material": {"type": "string", "description": "Material name (e.g. 'rebar', 'concrete C30/37', 'GGBS')"}},
                              "required": ["material"],
                },
      },
      {
                "name": "estimate_embodied_carbon",
                "description": "Run a cradle-to-gate (A1-A3) LCA on a project bill of materials. Returns total tCO2e, hotspot breakdown, and lower-carbon substitution options.",
                "input_schema": {
                              "type": "object",
                              "properties": {
                                                "materials_json": {
                                                                      "type": "string",
                                                                      "description": 'JSON array: [{"material": "concrete C32/40", "quantity": 500, "unit": "m3"}, ...]',
                                                }
                              },
                              "required": ["materials_json"],
                },
      },
      {
                "name": "load_history",
                "description": "Load previous briefing summaries to track carbon trends over time.",
                "input_schema": {
                              "type": "object",
                              "properties": {"n_last": {"type": "integer", "description": "How many past runs to load (default 5)", "default": 5}},
                },
      },
      {
                "name": "save_report",
                "description": "Save today's ESG briefing as markdown + PDF and record metrics in history.",
                "input_schema": {
                              "type": "object",
                              "properties": {
                                                "markdown": {"type": "string", "description": "Full markdown text of the briefing"},
                                                "metrics_json": {
                                                                      "type": "string",
                                                                      "description": 'JSON: {"headline": "...", "top_material": "...", "total_tco2e": 123.4}',
                                                },
                              },
                              "required": ["markdown"],
                },
      },
      {
                "name": "openai_analysis",
                "description": "Send a prompt to GPT-4o for a second-opinion cross-check. Use to validate LCA results, interpret dense regulatory text (e.g. EU CBAM), or get an alternative framing of carbon recommendations. Gracefully skipped if OPENAI_API_KEY is not set.",
                "input_schema": {
                              "type": "object",
                              "properties": {
                                                "prompt": {"type": "string", "description": "The question or analysis request for GPT-4o"},
                                                "context": {"type": "string", "description": "Optional system context (e.g. paste of a regulation excerpt or LCA output to review)"},
                              },
                              "required": ["prompt"],
                },
      },
]
