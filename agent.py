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

import google.generativeai as genai

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
        {"material": "rebar",           "quantity": 95,  "unit": "t"},
        {"material": "structural steel","quantity": 60,  "unit": "t"},
        {"material": "aluminium",       "quantity": 8,   "unit": "t"},
        {"material": "glass",           "quantity": 22,  "unit": "t"},
        {"material": "mineral wool",    "quantity": 12,  "unit": "t"},
    ])
    print("Sample project — mid-rise concrete-frame office:\n")
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

# ──────────────────────────────────────────────────────────────────────────
# Gemini tool schema conversion
# ──────────────────────────────────────────────────────────────────────────

def _build_gemini_tools(tool_defs):
    """Convert Anthropic-style tool definitions to Gemini FunctionDeclarations."""
    type_map = {
        "string": genai.protos.Type.STRING,
        "integer": genai.protos.Type.INTEGER,
        "number": genai.protos.Type.NUMBER,
        "boolean": genai.protos.Type.BOOLEAN,
        "array": genai.protos.Type.ARRAY,
        "object": genai.protos.Type.OBJECT,
    }
    declarations = []
    for t in tool_defs:
        schema = t.get("input_schema", {})
        props = {}
        for prop_name, prop_def in schema.get("properties", {}).items():
            g_type = type_map.get(prop_def.get("type", "string"), genai.protos.Type.STRING)
            props[prop_name] = genai.protos.Schema(
                type=g_type,
                description=prop_def.get("description", ""),
            )
        declarations.append(
            genai.protos.FunctionDeclaration(
                name=t["name"],
                description=t.get("description", ""),
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties=props,
                    required=schema.get("required", []),
                ),
            )
        )
    return [genai.protos.Tool(function_declarations=declarations)]

# ──────────────────────────────────────────────────────────────────────────
# Main agentic loop
# ──────────────────────────────────────────────────────────────────────────

def run_agent():
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    gemini_tools = _build_gemini_tools(TOOL_DEFINITIONS)
    model = genai.GenerativeModel(
        model_name=MODEL,
        system_instruction=get_system_prompt(),
        tools=gemini_tools,
    )
    chat = model.start_chat()

    print(f"\n{'─'*64}")
    print(f"🌍 ESG Intelligence Agent · focus: {FOCUS_REGION} · model: {MODEL}")
    print(f"{'─'*64}")

    response = chat.send_message(DAILY_QUESTION)

    step = 0
    while step < MAX_STEPS:
        step += 1
        log("STEP", f"{step}/{MAX_STEPS}", "90")

        candidate = response.candidates[0]
        finish_reason = candidate.finish_reason

        text_parts = []
        fn_calls = []
        for part in candidate.content.parts:
            if hasattr(part, "text") and part.text:
                text_parts.append(part.text)
            if hasattr(part, "function_call") and part.function_call.name:
                fn_calls.append(part.function_call)

        for text in text_parts:
            log("THINKING", text.strip()[:220], "93")

        if fn_calls:
            tool_response_parts = []
            for fc in fn_calls:
                tool_name = fc.name
                tool_args = dict(fc.args)
                log("TOOL", f"{tool_name}({list(tool_args.keys())})", "94")
                result = run_tool(tool_name, tool_args)
                log("RESULT", result[:300], "92")
                tool_response_parts.append(
                    genai.protos.Part(
                        function_response=genai.protos.FunctionResponse(
                            name=tool_name,
                            response={"result": result},
                        )
                    )
                )
            response = chat.send_message(tool_response_parts)
            continue

        # No function calls — model is done
        final_text = "\n".join(text_parts).strip()
        if final_text:
            log("FINAL", final_text[:500], "92")
        print("\n✅ Briefing complete.")
        break
    else:
        print(f"\n⚠️  Reached max steps ({MAX_STEPS}).")

# ──────────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if "--show-last" in sys.argv:
        show_last_report()
    elif "--demo-lca" in sys.argv:
        demo_lca()
    else:
        run_agent()
