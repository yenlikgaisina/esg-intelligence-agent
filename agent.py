"""
agent.py — ESG Intelligence Agent

Runs every morning to scan ESG reports, construction news, and sustainability
regulations, track embodied-carbon trends, run an automated A1-A3 LCA, and
generate a branded PDF briefing for construction/built-environment clients.

Built for the Kazakhstan + global construction market (with a CBAM lens), this
adapts the daily-monitor agent pattern into a sustainability intelligence tool.

Usage:
    python agent.py                # run today's briefing now
    python agent.py --show-last    # print the most recent briefing
    python agent.py --demo-lca     # run a sample embodied-carbon estimate only

Automate it:
    Mac/Linux cron:  0 7 * * *  cd /path/to/esg-intelligence-agent && python agent.py
    Or use the included GitHub Actions workflow (.github/workflows/daily-esg-brief.yml).
"""

import os
import sys
import json
import glob

import anthropic

from tools import TOOL_DEFINITIONS, TOOL_FUNCTIONS
from prompts import get_system_prompt
from config import MODEL, MAX_TOKENS, MAX_STEPS, REPORTS_DIR, FOCUS_REGION


# ──────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────

def log(label: str, text: str, color: str = "0"):
    print(f"\033[{color}m[{label}]\033[0m {text}")


def run_tool(name: str, inputs: dict) -> str:
    if name not in TOOL_FUNCTIONS:
        return f"Unknown tool: {name}"
    try:
        result = TOOL_FUNCTIONS[name](**inputs)
        return result if isinstance(result, str) else json.dumps(result)
    except Exception as e:
        return f"Tool error in {name}: {e}"


def show_last_report():
    reports = sorted(glob.glob(os.path.join(REPORTS_DIR, "esg_brief_*.md")), reverse=True)
    if not reports:
        print("No briefings found yet. Run `python agent.py` first.")
        return
    latest = reports[0]
    print(f"\n📄 {latest}\n{'─'*64}\n")
    with open(latest, encoding="utf-8") as f:
        print(f.read())


def demo_lca():
    """Run the automated LCA engine on a sample project — no API key needed."""
    from tools import estimate_embodied_carbon
    sample = json.dumps([
        {"material": "concrete C32/40", "quantity": 850, "unit": "m3"},
        {"material": "rebar", "quantity": 95, "unit": "t"},
        {"material": "structural steel", "quantity": 60, "unit": "t"},
        {"material": "aluminium", "quantity": 8, "unit": "t"},
        {"material": "glass", "quantity": 22, "unit": "t"},
        {"material": "mineral wool", "quantity": 12, "unit": "t"},
    ])
    print("Sample project — mid-rise concrete-frame office:\n")
    print(estimate_embodied_carbon(sample))


DAILY_QUESTION = f"""
Produce today's ESG intelligence briefing for the {FOCUS_REGION} construction market.

Follow your process exactly: load history first; scan all four streams (ESG reports,
construction news, regulations with a CBAM lens, embodied carbon); read at least 3
sources in full; run at least one automated embodied-carbon estimate; connect the
regulation/news to the carbon numbers and to concrete client actions; then save_report
with the full markdown and a metrics JSON.

Be specific, quantitative, and senior. This briefing goes to construction clients.
"""


# ──────────────────────────────────────────────────────────────────────────
# Main loop
# ──────────────────────────────────────────────────────────────────────────

def run_agent():
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    messages = [{"role": "user", "content": DAILY_QUESTION}]

    print(f"\n{'─'*64}")
    print(f"🌍  ESG Intelligence Agent  ·  focus: {FOCUS_REGION}  ·  model: {MODEL}")
    print(f"{'─'*64}")

    step = 0
    while step < MAX_STEPS:
        step += 1
        log("STEP", f"{step}/{MAX_STEPS}", "90")

        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=get_system_prompt(),
            tools=TOOL_DEFINITIONS,
            messages=messages,
        )

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "text" and block.text.strip():
                    log("THINKING", block.text.strip()[:220], "93")
                if block.type == "tool_use":
                    name, inputs = block.name, block.input
                    if name == "web_search":
                        log("SEARCH", f'[{inputs.get("focus","general")}] {inputs.get("query","")}', "95")
                    elif name == "read_page":
                        log("READ", inputs.get("url", "")[:80], "94")
                    elif name == "lookup_carbon_factor":
                        log("CARBON", f'lookup: {inputs.get("material","(catalogue)")}', "96")
                    elif name == "estimate_embodied_carbon":
                        log("LCA", "running embodied-carbon estimate...", "96")
                    elif name == "load_history":
                        log("HISTORY", "loading previous briefing...", "96")
                    elif name == "save_report":
                        log("SAVING", "writing report + rendering PDF...", "92")

                    result = run_tool(name, inputs)
                    log("→", result[:200].replace("\n", " "), "90")
                    tool_results.append({
                        "type": "tool_result", "tool_use_id": block.id, "content": result,
                    })

            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

        elif response.stop_reason == "end_turn":
            for block in response.content:
                if block.type == "text" and block.text.strip():
                    log("AGENT", block.text.strip()[:400], "93")
            print(f"\n{'─'*64}")
            print(f"✅ Done in {step} steps.")
            reports = sorted(glob.glob(os.path.join(REPORTS_DIR, "esg_brief_*.md")), reverse=True)
            if reports:
                print(f"📄 Latest briefing: {reports[0]}")
                pdf = reports[0].replace(".md", ".pdf")
                if os.path.exists(pdf):
                    print(f"📑 PDF: {pdf}")
            break
        else:
            log("WARNING", f"Unexpected stop: {response.stop_reason}", "91")
            break
    else:
        print(f"\n⚠️  Hit step limit ({MAX_STEPS}).")


# ──────────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if "--show-last" in sys.argv:
        show_last_report()
        sys.exit(0)
    if "--demo-lca" in sys.argv:
        demo_lca()
        sys.exit(0)

    missing = [k for k in ("ANTHROPIC_API_KEY", "TAVILY_API_KEY") if not os.getenv(k)]
    if missing:
        for key in missing:
            print(f"❌ Missing: {key}")
        print("\nSet them (or put them in a .env file):")
        print("  export ANTHROPIC_API_KEY=sk-ant-...")
        print("  export TAVILY_API_KEY=tvly-...")
        print("\nTip: `python agent.py --demo-lca` runs the LCA engine with no keys needed.")
        sys.exit(1)

    run_agent()
