"""
carbon_data.py — Embodied carbon factor database.

This is the engine that makes the agent "1clickLCA but automated": a curated
table of cradle-to-gate (life-cycle stages A1-A3) embodied carbon factors for
common construction materials, plus densities for volume->mass conversion and a
map of lower-carbon / circular-economy substitutions.

VALUES ARE INDICATIVE. They are drawn from openly published ranges
(ICE Database v3, generic industry-average EPDs). For a real LCA submission you
should always use product-specific Environmental Product Declarations (EPDs).
The agent treats these as a fast baseline and flags when a material is missing.

Units:
  factor   = kgCO2e per kg of material  (modules A1-A3, cradle-to-gate)
  density  = kg per m3  (for converting a volume to a mass)
"""

# ──────────────────────────────────────────────────────────────────────────
# MATERIAL DATABASE
# key is a normalised lowercase name; `aliases` lets the agent match free text.
# ──────────────────────────────────────────────────────────────────────────

MATERIALS = {
    # ---- Cement & concrete ----
    "cement_cem_i": {
        "name": "Portland cement (CEM I)",
        "category": "Cement & concrete",
        "factor": 0.86, "density": 1440,
        "aliases": ["portland cement", "cem i", "opc", "ordinary portland cement"],
        "source": "ICE v3 (indicative)",
    },
    "cement_ggbs_blend": {
        "name": "Blended cement, 50% GGBS",
        "category": "Cement & concrete",
        "factor": 0.43, "density": 1440,
        "aliases": ["ggbs cement", "slag cement", "blended cement", "cem iii"],
        "source": "ICE v3 (indicative)",
    },
    "concrete_c25_30": {
        "name": "Concrete C25/30 (generic)",
        "category": "Cement & concrete",
        "factor": 0.103, "density": 2400,
        "aliases": ["concrete", "rc25", "c25/30", "ready mix concrete"],
        "source": "ICE v3 (indicative)",
    },
    "concrete_c32_40": {
        "name": "Concrete C32/40 (generic)",
        "category": "Cement & concrete",
        "factor": 0.120, "density": 2400,
        "aliases": ["c32/40", "rc32", "structural concrete"],
        "source": "ICE v3 (indicative)",
    },
    "concrete_c32_40_50ggbs": {
        "name": "Concrete C32/40, 50% GGBS",
        "category": "Cement & concrete",
        "factor": 0.073, "density": 2400,
        "aliases": ["low carbon concrete", "ggbs concrete", "green concrete"],
        "source": "ICE v3 (indicative)",
    },
    "mortar": {
        "name": "Cement:sand mortar",
        "category": "Cement & concrete",
        "factor": 0.16, "density": 1800,
        "aliases": ["mortar", "screed"],
        "source": "ICE v3 (indicative)",
    },

    # ---- Steel & metals ----
    "steel_rebar_recycled": {
        "name": "Reinforcing steel (rebar, EAF recycled)",
        "category": "Steel & metals",
        "factor": 0.68, "density": 7850,
        "aliases": ["rebar", "reinforcement", "reinforcing steel", "rebar recycled"],
        "source": "ICE v3 (indicative)",
    },
    "steel_section": {
        "name": "Structural steel section (UK avg)",
        "category": "Steel & metals",
        "factor": 1.55, "density": 7850,
        "aliases": ["structural steel", "steel beam", "steel section", "i-beam"],
        "source": "ICE v3 (indicative)",
    },
    "steel_primary": {
        "name": "Steel, primary (BF-BOF)",
        "category": "Steel & metals",
        "factor": 2.46, "density": 7850,
        "aliases": ["primary steel", "virgin steel", "blast furnace steel"],
        "source": "ICE v3 (indicative)",
    },
    "stainless_steel": {
        "name": "Stainless steel",
        "category": "Steel & metals",
        "factor": 6.15, "density": 7850,
        "aliases": ["stainless", "inox"],
        "source": "ICE v3 (indicative)",
    },
    "aluminium_recycled": {
        "name": "Aluminium, high recycled content",
        "category": "Steel & metals",
        "factor": 2.30, "density": 2700,
        "aliases": ["recycled aluminium", "aluminium recycled"],
        "source": "ICE v3 (indicative)",
    },
    "aluminium_extruded": {
        "name": "Aluminium, extruded (avg)",
        "category": "Steel & metals",
        "factor": 8.16, "density": 2700,
        "aliases": ["aluminium", "aluminum", "aluminium extrusion", "curtain wall frame"],
        "source": "ICE v3 (indicative)",
    },
    "copper": {
        "name": "Copper (avg recycled content)",
        "category": "Steel & metals",
        "factor": 2.71, "density": 8960,
        "aliases": ["copper", "copper pipe", "copper wiring"],
        "source": "ICE v3 (indicative)",
    },

    # ---- Timber & bio-based ----
    "timber_softwood": {
        "name": "Sawn softwood (excl. biogenic)",
        "category": "Timber & bio-based",
        "factor": 0.26, "density": 500,
        "aliases": ["timber", "softwood", "sawn timber", "lumber", "wood"],
        "source": "ICE v3 (indicative)",
    },
    "clt": {
        "name": "Cross-laminated timber (CLT)",
        "category": "Timber & bio-based",
        "factor": 0.44, "density": 480,
        "aliases": ["clt", "cross laminated timber", "mass timber"],
        "source": "EPD industry avg (indicative)",
    },
    "glulam": {
        "name": "Glued-laminated timber (glulam)",
        "category": "Timber & bio-based",
        "factor": 0.51, "density": 480,
        "aliases": ["glulam", "glued laminated timber"],
        "source": "EPD industry avg (indicative)",
    },
    "plywood": {
        "name": "Plywood",
        "category": "Timber & bio-based",
        "factor": 0.68, "density": 600,
        "aliases": ["plywood", "ply"],
        "source": "ICE v3 (indicative)",
    },

    # ---- Masonry ----
    "brick_clay": {
        "name": "Clay brick",
        "category": "Masonry",
        "factor": 0.24, "density": 1900,
        "aliases": ["brick", "clay brick", "fired brick"],
        "source": "ICE v3 (indicative)",
    },
    "block_concrete": {
        "name": "Concrete block (dense)",
        "category": "Masonry",
        "factor": 0.10, "density": 2000,
        "aliases": ["concrete block", "breeze block", "cmu"],
        "source": "ICE v3 (indicative)",
    },
    "block_aac": {
        "name": "Aerated concrete block (AAC)",
        "category": "Masonry",
        "factor": 0.30, "density": 600,
        "aliases": ["aac", "aerated block", "aircrete"],
        "source": "ICE v3 (indicative)",
    },
    "stone_natural": {
        "name": "Natural stone",
        "category": "Masonry",
        "factor": 0.08, "density": 2600,
        "aliases": ["stone", "granite", "limestone", "natural stone"],
        "source": "ICE v3 (indicative)",
    },

    # ---- Glass, finishes, insulation ----
    "glass_float": {
        "name": "Float glass",
        "category": "Glass & finishes",
        "factor": 1.44, "density": 2500,
        "aliases": ["glass", "float glass", "glazing"],
        "source": "ICE v3 (indicative)",
    },
    "plasterboard": {
        "name": "Gypsum plasterboard",
        "category": "Glass & finishes",
        "factor": 0.39, "density": 800,
        "aliases": ["plasterboard", "drywall", "gypsum board", "gyproc"],
        "source": "ICE v3 (indicative)",
    },
    "ceramic_tile": {
        "name": "Ceramic tile",
        "category": "Glass & finishes",
        "factor": 0.78, "density": 2000,
        "aliases": ["ceramic tile", "tiles", "porcelain tile"],
        "source": "ICE v3 (indicative)",
    },
    "paint": {
        "name": "Paint (solvent based, avg)",
        "category": "Glass & finishes",
        "factor": 2.54, "density": 1300,
        "aliases": ["paint", "coating"],
        "source": "ICE v3 (indicative)",
    },
    "insulation_mineral_wool": {
        "name": "Mineral wool insulation",
        "category": "Insulation",
        "factor": 1.28, "density": 40,
        "aliases": ["mineral wool", "rock wool", "glass wool", "rockwool"],
        "source": "ICE v3 (indicative)",
    },
    "insulation_eps": {
        "name": "EPS insulation",
        "category": "Insulation",
        "factor": 3.29, "density": 20,
        "aliases": ["eps", "expanded polystyrene", "styrofoam"],
        "source": "ICE v3 (indicative)",
    },
    "insulation_xps": {
        "name": "XPS insulation",
        "category": "Insulation",
        "factor": 3.42, "density": 35,
        "aliases": ["xps", "extruded polystyrene"],
        "source": "ICE v3 (indicative)",
    },
    "insulation_cellulose": {
        "name": "Cellulose insulation",
        "category": "Insulation",
        "factor": 0.47, "density": 50,
        "aliases": ["cellulose", "cellulose insulation", "recycled paper insulation"],
        "source": "EPD industry avg (indicative)",
    },
    "insulation_woodfibre": {
        "name": "Wood-fibre insulation",
        "category": "Insulation",
        "factor": 0.55, "density": 50,
        "aliases": ["wood fibre", "woodfibre", "wood fiber insulation"],
        "source": "EPD industry avg (indicative)",
    },

    # ---- Other ----
    "bitumen": {
        "name": "Bitumen / asphalt",
        "category": "Other",
        "factor": 0.18, "density": 2300,
        "aliases": ["bitumen", "asphalt", "tarmac"],
        "source": "ICE v3 (indicative)",
    },
    "pvc": {
        "name": "PVC",
        "category": "Other",
        "factor": 3.10, "density": 1400,
        "aliases": ["pvc", "upvc", "pvc pipe"],
        "source": "ICE v3 (indicative)",
    },
}


# ──────────────────────────────────────────────────────────────────────────
# CIRCULAR-ECONOMY / LOW-CARBON SUBSTITUTIONS
# Maps a (high-carbon) material key -> a recommended lower-carbon alternative.
# This is the "circular economy" lens: specify recycled, blended, or bio-based.
# ──────────────────────────────────────────────────────────────────────────

SUBSTITUTIONS = {
    "cement_cem_i":       ("cement_ggbs_blend", "Replace ~50% clinker with GGBS or fly ash."),
    "concrete_c25_30":    ("concrete_c32_40_50ggbs", "Specify GGBS/fly-ash blended concrete mix."),
    "concrete_c32_40":    ("concrete_c32_40_50ggbs", "Specify GGBS/fly-ash blended concrete mix."),
    "steel_primary":      ("steel_rebar_recycled", "Source EAF (electric-arc-furnace) recycled steel."),
    "steel_section":      ("steel_rebar_recycled", "Maximise recycled content; reuse reclaimed sections."),
    "aluminium_extruded": ("aluminium_recycled", "Specify high recycled-content aluminium."),
    "insulation_eps":     ("insulation_cellulose", "Switch to cellulose or wood-fibre insulation."),
    "insulation_xps":     ("insulation_woodfibre", "Switch to wood-fibre or mineral-wool insulation."),
}


# ──────────────────────────────────────────────────────────────────────────
# LOOKUP HELPERS
# ──────────────────────────────────────────────────────────────────────────

def _has_grade(s: str) -> bool:
    """True if the string carries a distinguishing grade/spec (digits or a slash)."""
    return any(ch.isdigit() for ch in s) or "/" in s


def find_material(query: str):
    """
    Fuzzy-match a free-text material name to a database key, scoring candidates so
    that a specific grade (e.g. 'concrete C32/40') beats a generic alias ('concrete').
    Returns (key, record) or (None, None).
    """
    q = (query or "").strip().lower()
    if not q:
        return None, None
    if q in MATERIALS:
        return q, MATERIALS[q]

    best_key, best_rec, best_score = None, None, 0.0
    for key, rec in MATERIALS.items():
        score = 0.0
        if q == rec["name"].lower():
            score = 1000
        for alias in rec.get("aliases", []):
            if q == alias:
                score = max(score, 900)
            elif alias in q:                      # alias is a substring of the query
                s = 100 + len(alias) + (40 if _has_grade(alias) else 0)
                score = max(score, s)
            elif q in alias:                      # query is a substring of the alias
                score = max(score, 50 + len(q))
        if score == 0 and any(tok in rec["name"].lower() for tok in q.split() if len(tok) > 2):
            score = 10                            # loose token-overlap fallback
        if score > best_score:
            best_key, best_rec, best_score = key, rec, score

    return (best_key, best_rec) if best_rec else (None, None)


def list_materials():
    """Return a compact catalogue grouped by category for the agent / docs."""
    by_cat = {}
    for key, rec in MATERIALS.items():
        by_cat.setdefault(rec["category"], []).append(
            {"key": key, "name": rec["name"], "factor_kgco2e_per_kg": rec["factor"]}
        )
    return by_cat
