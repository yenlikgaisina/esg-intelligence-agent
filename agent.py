"""
agent.py - ESG Intelligence Agent
Runs every morning to scan ESG reports, construction news, and sustainability
regulations, track embodied-carbon trends, run an automated A1-A3 LCA, and
generate a branded PDF briefing for construction/built-environment clients.
Built for the Kazakhstan + global construction market (with a CBAM lens), this
adapts the daily-monitor agent pattern into a sustainability intelligence tool.
Usage:
    python agent.py              # run today's briefing now
    python agent.py --show-last  # print the most recent briefing
    python agent.py --demo-lca   # run a sample embodied-carbon estimate only
Automate it:
    Mac/Linux cron:  0 7 * * *  cd /path/to/esg-intelligence-agent && python agent.py
    Or use the included GitHub Actions workflow (.github/workflows/daily-esg-brief.yml).
"""

import os
import sys
import json
import glob

from openai import OpenAI

from tools import TOOL_DEFINITIONS, TOOL_FUNCTIONS
from prompts import get_system_prompt
from config import MODEL, MAX_TOKENS, MAX_STEPS, REPORTS_DIR, FOCUS_REGION

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def log(label, text, color="0"):
    print(f"\033[{color}m[{label}]\033[0m {text}")

def run_tool(name, inputs):
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
        print("No briefings found yet.")
        return
    latest = reports[0]
    print(f"\n{latest}\n")
    with open(latest, encoding="utf-8") as f:
        print(f.read())

def demo_lca():
    from tools import estimate_embodied_carbon
    sample = json.dumps([
        {"material": "concrete C32/40", "quantity": 850, "unit": "m3"},
        {"material": "rebar",           "quantity": 95,  "unit": "t"},
        {"material": "structural steel","quantity": 60,  "unit": "t"},
        {"material": "aluminium",        "quantity": 8,   "unit": "t"},
        {"material": "glass",            "quantity": 22,  "unit": "t"},
        {"material": "mineral wool",     "quantity": 12,  "unit": "t"},
    ])
    print("Sample project - mid-rise concrete-frame office:\n")
    print(estimate_embodied_carbon(sample))

DAILY_QUESTION = (
    f"Produce today's ESG intelligence briefing for the {FOCUS_REGION} construction market. "
    "Follow your process exactly: load history first; scan all four streams (ESG reports, "
    "construction news, regulations with a CBAM lens, embodied carbon); read at least 3 "
    "sources in full; run at least one automated embodied-carbon estimate; connect the "
    "regulation/news to the carbon numbers and to concrete client actions; then save_report "
    "with the full markdown and a metrics JSON. "
    "Be specific, quantitative, and senior. This briefing goes to construction clients."
)

# ---------------------------------------------------------------------------
# Build OpenAI tool declarations from the existing Anthropic-style definitions
# ---------------------------------------------------------------------------

def _build_openai_tools(tool_defs):
    tools = []
    for t in tool_defs:
        schema = t.get("input_schema", {})
        tools.append({
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t.get("description", ""),
                "parameters": {
                    "type": "object",
                    "properties": schema.get("properties", {}),
                    "required": schema.get("required", []),
                },
            },
        })
    return tools

# ---------------------------------------------------------------------------
# Main agentic loop
# ---------------------------------------------------------------------------

def run_agent():
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    openai_tools = _build_openai_tools(TOOL_DEFINITIONS)
    system_prompt = get_system_prompt()

    print(f"\n{'='*64}")
    print(f"ESG Intelligence Agent - focus: {FOCUS_REGION} - model: {MODEL}")
    print(f"{'='*64}")

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": DAILY_QUESTION},
    ]

    step = 0
    while step < MAX_STEPS:
        step += 1
        log("STEP", f"{step}/{MAX_STEPS}", "90")

        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=openai_tools,
            max_tokens=MAX_TOKENS,
        )

        message = response.choices[0].message
        tool_calls = message.tool_calls or []

        if message.content:
            log("THINKING", message.content.strip()[:220], "93")

        # Append the assistant turn to history (must include tool_calls if present)
        messages.append({
            "role": "assistant",
            "content": message.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in tool_calls
            ] if tool_calls else None,
        })

        if tool_calls:
            for tc in tool_calls:
                tool_name = tc.function.name
                try:
                    tool_args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                except json.JSONDecodeError:
                    tool_args = {}
                log("TOOL", f"{tool_name}({list(tool_args.keys())})", "94")
                result = run_tool(tool_name, tool_args)
                log("RESULT", result[:300], "92")
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })
            continue

        # No tool calls - done
        final_text = (message.content or "").strip()
        if final_text:
            log("FINAL", final_text[:500], "92")
        print("\nBriefing complete.")
        break
    else:
        print(f"\nReached max steps ({MAX_STEPS}).")

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if "--show-last" in sys.argv:
        show_last_report()
    elif "--demo-lca" in sys.argv:
        demo_lca()
    else:
        run_agent()
