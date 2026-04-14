"""
UC-0A — Complaint Classifier
classifier.py

Role    (agents.md): City operations complaint classifier for the Director's dashboard.
Intent  (agents.md): Consistent taxonomy, accurate severity detection, honest ambiguity handling.
Skills  (skills.md): classify_complaint, batch_classify

Run:
    python classifier.py --input ../data/city-test-files/test_pune.csv \
                         --output results_pune.csv
"""
import argparse
import csv
import re
import sys

# ---------------------------------------------------------------------------
# Schema — enforcement rules from agents.md
# ---------------------------------------------------------------------------

ALLOWED_CATEGORIES = {
    "Pothole", "Flooding", "Streetlight", "Waste", "Noise",
    "Road Damage", "Heritage Damage", "Heat Hazard", "Drain Blockage", "Other",
}

# Every description containing these words must produce priority: Urgent
SEVERITY_KEYWORDS = {
    "injury", "child", "school", "hospital", "ambulance",
    "fire", "hazard", "fell", "collapse",
}

# Ordered from most-specific to least-specific to avoid false matches
CATEGORY_PATTERNS = [
    ("Drain Blockage",  ["drain blocked", "drain blockage", "drain clogged",
                         "blocked drain", "sewage blocked"]),
    ("Flooding",        ["flood", "flooded", "waterlogged", "knee-deep",
                         "standing in water", "water stagnation", "inundated"]),
    ("Pothole",         ["pothole", "pot hole", "tyre damage", "crater"]),
    ("Streetlight",     ["streetlight", "street light", "street-light",
                         "lamp post", "lamppost", "sparking light",
                         "flickering light", "lights out", "light out"]),
    ("Waste",           ["garbage", "waste", "overflowing bin", "rubbish",
                         "litter", "trash", "dumping"]),
    ("Noise",           ["noise", "loud music", "music past midnight",
                         "blaring", "sound disturbance", "loud party"]),
    ("Road Damage",     ["road surface", "cracked road", "road cracked",
                         "sinking road", "road damage", "damaged road",
                         "surface cracked", "road sinking"]),
    ("Heritage Damage", ["heritage", "monument", "historical", "fort",
                         "temple", "ancient structure"]),
    ("Heat Hazard",     ["heat stroke", "heat wave", "extreme heat",
                         "no shade", "heat hazard"]),
]

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _detect_category(description: str):
    """Return (category, confident) using keyword matching."""
    desc_lower = description.lower()
    for category, keywords in CATEGORY_PATTERNS:
        for kw in keywords:
            if kw in desc_lower:
                return category, True
    return "Other", False


def _detect_priority(description: str) -> str:
    """Return 'Urgent' if any severity keyword is present, else 'Standard'."""
    desc_lower = description.lower()
    for kw in SEVERITY_KEYWORDS:
        if re.search(r"\b" + re.escape(kw) + r"\b", desc_lower):
            return "Urgent"
    return "Standard"


def _build_reason(description: str, category: str) -> str:
    """One sentence citing specific words from the description (agents.md rule 3)."""
    snippet = description if len(description) <= 120 else description[:117] + "..."
    return f"Classified as '{category}' based on complaint: \"{snippet}\""


# ---------------------------------------------------------------------------
# Skill: classify_complaint  (skills.md)
# ---------------------------------------------------------------------------

def classify_complaint(row: dict) -> dict:
    """
    Classify a single complaint row.

    Input:  dict with at least a 'description' field (and optional location fields).
    Output: dict with complaint_id, category, priority, reason, flag.
    Error:  vague/short descriptions → category: Other, flag: NEEDS_REVIEW.
    """
    description = (row.get("description") or "").strip()
    complaint_id = row.get("complaint_id", "")

    # Guard: vague or missing description
    if not description or len(description) < 5:
        return {
            "complaint_id": complaint_id,
            "category": "Other",
            "priority": "Standard",
            "reason": "Description is too vague or missing to classify confidently.",
            "flag": "NEEDS_REVIEW",
        }

    category, confident = _detect_category(description)
    priority = _detect_priority(description)
    reason = _build_reason(description, category)
    flag = "" if confident else "NEEDS_REVIEW"

    return {
        "complaint_id": complaint_id,
        "category": category,
        "priority": priority,
        "reason": reason,
        "flag": flag,
    }


# ---------------------------------------------------------------------------
# Skill: batch_classify  (skills.md)
# ---------------------------------------------------------------------------

def batch_classify(input_path: str, output_path: str):
    """
    Read input CSV, classify each row, write results CSV.

    Input:  path to a city test CSV file.
    Output: path to results CSV with original fields + category, priority, reason, flag.
    Error:  malformed rows are logged with row number and skipped; processing continues.
    """
    output_fields = [
        "complaint_id", "date_raised", "city", "ward", "location",
        "description", "reported_by", "days_open",
        "category", "priority", "reason", "flag",
    ]

    rows_written = 0
    rows_skipped = 0

    with open(input_path, newline="", encoding="utf-8") as infile, \
         open(output_path, "w", newline="", encoding="utf-8") as outfile:

        reader = csv.DictReader(infile)
        writer = csv.DictWriter(outfile, fieldnames=output_fields)
        writer.writeheader()

        for i, row in enumerate(reader, start=2):  # row 1 is the header
            try:
                result = classify_complaint(row)
                merged = {**row, **result}
                writer.writerow({k: merged.get(k, "") for k in output_fields})
                rows_written += 1
            except Exception as exc:
                print(f"[SKIP] Row {i} malformed — {exc}", file=sys.stderr)
                rows_skipped += 1

    print(f"Classified {rows_written} rows. Skipped {rows_skipped} malformed rows.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UC-0A Complaint Classifier")
    parser.add_argument("--input",  required=True, help="Path to input CSV file")
    parser.add_argument("--output", required=True, help="Path to output results CSV file")
    args = parser.parse_args()
    batch_classify(args.input, args.output)
    print(f"Done. Results written to {args.output}")
