"""
UC-0A — Complaint Classifier
classifier.py — Implementation based on agents.md and skills.md

Enforcement rules applied:
  1. CATEGORY ENUM RULE — fixed allowed list, no invented categories
  2. SEVERITY KEYWORD RULE — keyword scan triggers Urgent priority
  3. REASON FIELD RULE — every row gets a one-sentence reason citing the text
  4. AMBIGUITY REFUSAL RULE — vague/short → Other + NEEDS_REVIEW
  5. NO INVENTED CATEGORIES RULE — only allowed enum values emitted

Run:
  python classifier.py --input ../data/city-test-files/test_pune.csv --output results_pune.csv
"""

import argparse
import csv
import sys
import re

# ── Fixed taxonomy from agents.md enforcement ────────────────────────────────

ALLOWED_CATEGORIES = [
    "Pothole", "Flooding", "Streetlight", "Waste", "Noise",
    "Road Damage", "Heritage Damage", "Heat Hazard", "Drain Blockage", "Other"
]

SEVERITY_KEYWORDS = [
    "injury", "child", "school", "hospital", "ambulance",
    "fire", "hazard", "fell", "collapse"
]

# ── Keyword-to-category mapping ──────────────────────────────────────────────
# Each tuple: (list of keywords, category)
# Order matters — first match wins; more specific patterns come first.

CATEGORY_RULES = [
    (["pothole", "tyre damage", "crater"],                        "Pothole"),
    (["flood", "flooded", "waterlog", "water-log", "submerged",
      "knee-deep", "stranded"],                                   "Flooding"),
    (["streetlight", "street light", "lights out", "dark at night",
      "flickering", "sparking", "lamp post"],                     "Streetlight"),
    (["garbage", "waste", "rubbish", "trash", "overflowing bin",
      "dumped", "dead animal", "bulk waste", "litter"],           "Waste"),
    (["noise", "loud music", "music past midnight", "decibel",
      "honking", "sound pollution"],                              "Noise"),
    (["road surface", "crack", "sinking", "broken road",
      "road damage", "footpath", "tiles broken", "upturned",
      "manhole", "missing cover"],                                "Road Damage"),
    (["heritage", "monument", "historical", "old city",
      "heritage street"],                                         "Heritage Damage"),
    (["heat", "heatwave", "sunstroke", "temperature",
      "hot surface"],                                             "Heat Hazard"),
    (["drain", "blocked drain", "clogged", "sewer",
      "drain block", "nullah"],                                   "Drain Blockage"),
]

MIN_MEANINGFUL_WORDS = 5


# ── Skill: classify_complaint ────────────────────────────────────────────────

def classify_complaint(row: dict) -> dict:
    """
    Classify a single complaint row.
    Returns dict with: complaint_id, category, priority, reason, flag

    Applies all five enforcement rules from agents.md.
    """
    complaint_id = row.get("complaint_id", "UNKNOWN")
    description = row.get("description", "").strip()
    desc_lower = description.lower()

    # ── AMBIGUITY REFUSAL RULE ───────────────────────────────────────────
    meaningful_words = [w for w in re.findall(r"[a-zA-Z]+", description) if len(w) > 1]
    if not description or len(meaningful_words) < MIN_MEANINGFUL_WORDS:
        return {
            "complaint_id": complaint_id,
            "category": "Other",
            "priority": "Low",
            "reason": "Description too vague or short for confident classification.",
            "flag": "NEEDS_REVIEW",
        }

    # ── SEVERITY KEYWORD RULE ────────────────────────────────────────────
    matched_severity = [kw for kw in SEVERITY_KEYWORDS if kw in desc_lower]
    priority = "Urgent" if matched_severity else "Standard"

    # ── CATEGORY ENUM RULE + NO INVENTED CATEGORIES RULE ─────────────────
    category = None
    matched_cat_keywords = []

    for keywords, cat in CATEGORY_RULES:
        hits = [kw for kw in keywords if kw in desc_lower]
        if hits:
            category = cat
            matched_cat_keywords = hits
            break  # first match wins

    flag = ""
    if category is None:
        category = "Other"
        flag = "NEEDS_REVIEW"

    # ── REASON FIELD RULE ────────────────────────────────────────────────
    if matched_cat_keywords and matched_severity:
        reason = (
            f"Classified as {category} due to mention of "
            f"{', '.join(repr(k) for k in matched_cat_keywords)}; "
            f"priority Urgent due to severity keyword "
            f"{', '.join(repr(k) for k in matched_severity)}."
        )
    elif matched_cat_keywords:
        reason = (
            f"Classified as {category} due to mention of "
            f"{', '.join(repr(k) for k in matched_cat_keywords)} "
            f"in the description."
        )
    elif flag == "NEEDS_REVIEW":
        reason = (
            "Description does not clearly map to a single category."
        )
    else:
        reason = f"Classified as {category} based on overall description."

    return {
        "complaint_id": complaint_id,
        "category": category,
        "priority": priority,
        "reason": reason,
        "flag": flag,
    }


# ── Skill: batch_classify ───────────────────────────────────────────────────

def batch_classify(input_path: str, output_path: str):
    """
    Read input CSV, classify each row, write results CSV.

    Malformed rows are logged to stderr and skipped.
    Processing continues for all remaining rows.
    """
    results = []

    try:
        with open(input_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader, start=2):  # row 1 = header
                try:
                    result = classify_complaint(row)
                    results.append(result)
                except Exception as e:
                    print(
                        f"WARNING: Skipping malformed row {idx}: {e}",
                        file=sys.stderr,
                    )
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Input file not found: {input_path}. "
            f"Check the path and try again."
        )

    # Write results CSV
    fieldnames = ["complaint_id", "category", "priority", "reason", "flag"]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"Processed {len(results)} complaints.")


# ── CLI entry point ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UC-0A Complaint Classifier")
    parser.add_argument("--input", required=True, help="Path to input CSV file")
    parser.add_argument("--output", required=True, help="Path to output results CSV")
    args = parser.parse_args()
    batch_classify(args.input, args.output)
    print(f"Done. Results written to {args.output}")
