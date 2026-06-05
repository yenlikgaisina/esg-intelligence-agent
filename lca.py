"""
lca.py — A lightweight embodied-carbon (LCA) calculation engine.

Given a bill of materials, it computes cradle-to-gate (A1-A3) embodied carbon,
identifies the carbon "hotspots", and proposes circular-economy substitutions
with quantified savings. This is the automated core of the tool.

A "bill of materials" is a list of dicts, e.g.:
    [
      {"material": "concrete C32/40", "quantity": 120, "unit": "m3"},
      {"material": "rebar",           "quantity": 9.5, "unit": "t"},
      {"material": "structural steel","quantity": 40,  "unit": "t"},
    ]

Supported units: kg, t (tonne), m3 (uses material density), m2*thickness not
handled here — convert to m3 upstream.
"""

from carbon_data import MATERIALS, SUBSTITUTIONS, find_material


def _to_kg(quantity: float, unit: str, density: float):
    """Convert a quantity in kg / t / m3 to kilograms. Returns (kg, note)."""
    unit = (unit or "kg").strip().lower()
    if unit in ("kg", "kgs", "kilogram", "kilograms"):
        return float(quantity), None
    if unit in ("t", "tonne", "tonnes", "ton", "tons", "mt"):
        return float(quantity) * 1000.0, None
    if unit in ("m3", "m^3", "cubic metre", "cubic meter", "cum"):
        if not density:
            return None, "no density on record for volume conversion"
        return float(quantity) * float(density), None
    return None, f"unsupported unit '{unit}'"


def calculate(bill_of_materials):
    """
    Compute embodied carbon for a bill of materials.

    Returns a dict with: line items, total kgCO2e / tCO2e, hotspots,
    circular-economy recommendations with savings, and any unmatched materials.
    """
    line_items = []
    unmatched = []
    total_kg = 0.0

    for entry in bill_of_materials:
        raw_name = entry.get("material", "")
        qty = entry.get("quantity", 0)
        unit = entry.get("unit", "kg")

        key, rec = find_material(raw_name)
        if not rec:
            unmatched.append(raw_name)
            continue

        mass_kg, note = _to_kg(qty, unit, rec.get("density"))
        if mass_kg is None:
            unmatched.append(f"{raw_name} ({note})")
            continue

        co2e = mass_kg * rec["factor"]
        total_kg += co2e
        line_items.append({
            "input": raw_name,
            "matched_material": rec["name"],
            "key": key,
            "quantity": qty,
            "unit": unit,
            "mass_kg": round(mass_kg, 1),
            "factor_kgco2e_per_kg": rec["factor"],
            "embodied_kgco2e": round(co2e, 1),
            "source": rec["source"],
        })

    # Sort by impact, compute share
    line_items.sort(key=lambda x: x["embodied_kgco2e"], reverse=True)
    for li in line_items:
        li["share_pct"] = round(100 * li["embodied_kgco2e"] / total_kg, 1) if total_kg else 0.0

    # Hotspots = items making up the bulk of the footprint (top until ~80%)
    hotspots, cum = [], 0.0
    for li in line_items:
        hotspots.append(li)
        cum += li["share_pct"]
        if cum >= 80:
            break

    # Circular-economy recommendations with quantified savings
    recommendations = []
    for li in line_items:
        sub = SUBSTITUTIONS.get(li["key"])
        if not sub:
            continue
        sub_key, advice = sub
        sub_factor = MATERIALS[sub_key]["factor"]
        new_co2e = li["mass_kg"] * sub_factor
        saving = li["embodied_kgco2e"] - new_co2e
        if saving <= 0:
            continue
        recommendations.append({
            "material": li["matched_material"],
            "switch_to": MATERIALS[sub_key]["name"],
            "advice": advice,
            "current_kgco2e": round(li["embodied_kgco2e"], 1),
            "improved_kgco2e": round(new_co2e, 1),
            "saving_kgco2e": round(saving, 1),
            "saving_pct": round(100 * saving / li["embodied_kgco2e"], 1),
        })
    recommendations.sort(key=lambda x: x["saving_kgco2e"], reverse=True)

    total_saving = sum(r["saving_kgco2e"] for r in recommendations)

    return {
        "total_kgco2e": round(total_kg, 1),
        "total_tco2e": round(total_kg / 1000.0, 2),
        "line_items": line_items,
        "hotspots": [h["matched_material"] for h in hotspots],
        "recommendations": recommendations,
        "potential_saving_kgco2e": round(total_saving, 1),
        "potential_saving_pct": round(100 * total_saving / total_kg, 1) if total_kg else 0.0,
        "unmatched_materials": unmatched,
        "notes": (
            "Indicative cradle-to-gate (A1-A3) estimate using industry-average "
            "factors. Use product-specific EPDs for verified reporting."
        ),
    }
