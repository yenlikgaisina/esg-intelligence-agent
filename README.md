# 🌍 ESG Intelligence Agent

**An autonomous AI analyst for the construction & built-environment sector.**
Every morning it scans ESG reports, construction news, and sustainability
regulations, tracks embodied-carbon trends, runs an automated cradle-to-gate
life-cycle assessment (LCA), and generates a branded PDF briefing.

Think of it as **1clickLCA's embodied-carbon logic + a research analyst that never
sleeps** — automated, trend-aware, and tuned for the **Kazakhstan + global**
construction market with a built-in **EU CBAM** lens.

> Built on the agentic "daily monitor" pattern (a fixed question, fresh answers
> every run), adapted from a job-market tracker into a domain tool where the
> author has real expertise: data science + circular-economy / ESG advisory.

---

## Why this exists

Construction is responsible for a large share of global emissions, and the rules
are tightening fast — **EU CBAM** now puts a carbon price on imported steel,
cement and aluminium, which directly affects Kazakhstan's exporters. Clients need
to know, every week: *what changed, what it costs them in carbon, and what to do
about it.* This agent answers that automatically.

It combines three things into one tool:

- **Data-science engineering** — an agentic tool-use loop over the Anthropic API.
- **Circular-economy expertise** — every result surfaces lower-carbon, recycled,
  and material-substitution opportunities with quantified savings.
- **Consultancy value** — output is a client-ready intelligence briefing, not a
  data dump.

---

## What it does each run

| Stream | What it scans | Example signal |
|--------|---------------|----------------|
| 📊 ESG reports | corporate / sector sustainability disclosures | new Scope 3 commitments |
| 🏗️ Construction news | materials, projects, markets | low-carbon cement scale-up |
| 📜 Regulations | CBAM, CSRD/ESRS, EU Taxonomy, KZ/EAEU climate rules | CBAM definitive-period changes |
| 🧱 Embodied carbon | material carbon factors, EPDs | falling EAF-steel intensity |

It then runs an **automated A1–A3 LCA** on a representative project, identifies the
carbon **hotspots**, proposes **circular-economy substitutions with quantified
savings**, ties it all to **client actions**, and saves a **markdown + PDF** report.

---

## The automated LCA engine (the "1clickLCA" core)

A curated embodied-carbon database (`carbon_data.py`, ~35 materials, ICE v3 /
EPD-style indicative factors) plus a calculation engine (`lca.py`) that takes a
bill of materials and returns total tCO₂e, a hotspot breakdown, and ranked
low-carbon swaps.

```bash
python agent.py --demo-lca   # runs a sample estimate, no API key needed
```

```jsonc
// input: a bill of materials
[
  {"material": "concrete C32/40",  "quantity": 850, "unit": "m3"},
  {"material": "rebar",            "quantity": 95,  "unit": "t"},
  {"material": "structural steel", "quantity": 60,  "unit": "t"}
]
// output: total tCO2e, per-material share, hotspots,
//         and circular-economy swaps with quantified savings
```

Units supported: `kg`, `t`, `m3` (volume → mass via material density).

> ⚠️ Factors are **indicative cradle-to-gate** values for fast screening. For
> formal reporting, replace them with product-specific **EPDs**.

---

## Quick start

```bash
git clone https://github.com/yenlikgaisina/esg-intelligence-agent.git
cd esg-intelligence-agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env        # then add your two API keys
python agent.py             # generate today's briefing
python agent.py --show-last # print the most recent briefing
```

You need two keys (both have free tiers):
- `ANTHROPIC_API_KEY` — https://console.anthropic.com/
- `TAVILY_API_KEY` — https://tavily.com/

---

## Run it every morning

**GitHub Actions (recommended — runs in the cloud).** The included
[`.github/workflows/daily-esg-brief.yml`](.github/workflows/daily-esg-brief.yml)
runs daily, commits the new briefing back to the repo, and uploads it as an
artifact. Add `ANTHROPIC_API_KEY` and `TAVILY_API_KEY` under
**Settings → Secrets and variables → Actions**.

**Local cron (Mac/Linux):**
```cron
0 7 * * *  cd /path/to/esg-intelligence-agent && /path/to/.venv/bin/python agent.py
```

---

## How it works

```
agent.py        orchestrates the Anthropic tool-use loop (the "daily monitor")
prompts.py      the fixed analyst brief — what to scan and how to report
tools.py        6 tools: web_search · read_page · lookup_carbon_factor ·
                estimate_embodied_carbon · load_history · save_report
carbon_data.py  embodied-carbon factor database + circular-economy substitutions
lca.py          the A1–A3 embodied-carbon calculation engine
report.py       markdown → branded PDF (reportlab)
config.py       model, region focus, and paths (env-overridable)
```

Each run: `load_history` → multi-stream `web_search` → `read_page` the key
sources → `estimate_embodied_carbon` on a scenario → synthesise → `save_report`
(markdown + PDF + history for next-day trend comparison).

---

## Roadmap

- [ ] Email / Slack delivery of the morning PDF
- [ ] Pull live EPD data (e.g. ECO Platform, EPD International) instead of static factors
- [ ] Per-client watchlists (track named companies & projects)
- [ ] B1–B7 / C-stage (in-use & end-of-life) life-cycle modules
- [ ] CBAM cost calculator (carbon price × embodied carbon of exported goods)
- [ ] Russian / Kazakh-language briefing output

---

## License

MIT. Embodied-carbon factors are indicative and provided without warranty —
verify against product-specific EPDs before any formal or financial use.
