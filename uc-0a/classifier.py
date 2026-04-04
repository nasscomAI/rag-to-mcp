"""
UC-0A — Complaint Classifier
classifier.py — Classifies city complaints using R.I.C.E enforcement rules.

Run: python3 classifier.py --input ../data/city-test-files/test_pune.csv \
                           --output results_pune.csv
"""
import argparse
import csv
import re

ALLOWED_CATEGORIES = [
    "Pothole", "Flooding", "Streetlight", "Waste", "Noise",
    "Road Damage", "Heritage Damage", "Heat Hazard", "Drain Blockage", "Other"
]

SEVERITY_KEYWORDS = [
    "injur", "child", "school", "hospital", "ambulance",
    "fire", "hazard", "fell", "collaps"
]

# Keyword patterns for category detection (order matters — first match wins)
CATEGORY_PATTERNS = [
    ("Pothole",         [r"\bpotholes?\b"]),
    ("Flooding",        [r"\bfloods?\b", r"\bflooded\b", r"\bflooding\b", r"\bstranded\b", r"\bknee-deep\b",
                         r"\brainwater\b", r"\bwaterlogg"]),
    ("Drain Blockage",  [r"\bdrains?\b", r"\bmanhole\b", r"\bsewer\b", r"\bblocked drain\b", r"\bdraining\b"]),
    ("Streetlight",     [r"\bstreetlights?\b", r"\bstreet lights?\b", r"\blights? out\b", r"\bflickering\b",
                         r"\bunlit\b", r"\bdarkness\b", r"\bsubstation\b", r"\bwiring\b"]),
    ("Waste",           [r"\bgarbage\b", r"\bwaste\b", r"\brubbish\b", r"\boverflowing\b", r"\bdead animal\b",
                         r"\bnot removed\b", r"\bdumped\b"]),
    ("Noise",           [r"\bnoise\b", r"\bmusic\b", r"\bloud\b", r"\bmidnight\b", r"\bdrilling\b",
                         r"\bidling\b", r"\bband\b.*\bplaying\b", r"\bplaying\b.*\b(band|11\s*pm|midnight)"]),
    ("Road Damage",     [r"\broad.*crack\b", r"\bsinking\b", r"\bcracked\b", r"\bfootpath\b", r"\btiles? broken\b",
                         r"\bupturned\b", r"\bcollapsed?\b", r"\bcrater\b", r"\bbuckled\b", r"\bsubsided\b"]),
    ("Heritage Damage", [r"\bheritage\b", r"\bmonument\b", r"\bhistoric\b"]),
    ("Heat Hazard",     [r"\bheat\b", r"\bsunstroke\b", r"\bheatwave\b", r"\bmelting\b", r"\bbubbling\b",
                         r"\b\d{2,}°?\s*c\b", r"\btemperatures?\b", r"\bfull sun\b"]),
]


def _detect_category(description: str) -> tuple[str, bool]:
    """Return (category, confident) based on keyword matching."""
    desc_lower = description.lower()
    for category, patterns in CATEGORY_PATTERNS:
        for pattern in patterns:
            if re.search(pattern, desc_lower):
                return category, True
    return "Other", False


def _detect_priority(description: str) -> str:
    """Return Urgent if any severity keyword is found, else Standard."""
    desc_lower = description.lower()
    for keyword in SEVERITY_KEYWORDS:
        if re.search(rf"\b{keyword}", desc_lower):
            return "Urgent"
    return "Standard"


def _build_reason(description: str, category: str, priority: str) -> str:
    """Build a one-sentence reason citing specific words from the description."""
    desc_lower = description.lower()

    # Find which severity keywords triggered Urgent
    triggered_keywords = [
        kw for kw in SEVERITY_KEYWORDS
        if re.search(rf"\b{kw}", desc_lower)
    ]

    # Find which category pattern matched
    matched_pattern_words = []
    for cat, patterns in CATEGORY_PATTERNS:
        if cat == category:
            for pattern in patterns:
                match = re.search(pattern, desc_lower)
                if match:
                    matched_pattern_words.append(match.group())
            break

    parts = []
    if matched_pattern_words:
        parts.append(f"description contains '{matched_pattern_words[0]}' indicating {category}")
    if triggered_keywords:
        parts.append(f"severity keyword(s) [{', '.join(triggered_keywords)}] triggered Urgent priority")
    if not parts:
        parts.append("description did not match any known category pattern")

    return ". ".join(parts).capitalize() + "."


def classify_complaint(row: dict) -> dict:
    """
    Classify a single complaint row.
    Returns dict with: complaint_id, category, priority, reason, flag
    """
    complaint_id = row.get("complaint_id", "UNKNOWN")
    description = row.get("description", "").strip()

    # Vague/short descriptions -> Other + NEEDS_REVIEW
    if len(description) < 10:
        return {
            "complaint_id": complaint_id,
            "category": "Other",
            "priority": "Standard",
            "reason": "Description too short or vague for confident classification.",
            "flag": "NEEDS_REVIEW"
        }

    category, confident = _detect_category(description)
    priority = _detect_priority(description)
    reason = _build_reason(description, category, priority)
    flag = "" if confident else "NEEDS_REVIEW"

    return {
        "complaint_id": complaint_id,
        "category": category,
        "priority": priority,
        "reason": reason,
        "flag": flag
    }


def batch_classify(input_path: str, output_path: str):
    """Read input CSV, classify each row, write results CSV."""
    results = []
    skipped = []

    with open(input_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if "description" not in row or not row["description"].strip():
                skipped.append(i + 2)  # +2 for header + 0-index
                continue
            result = classify_complaint(row)
            results.append(result)

    fieldnames = ["complaint_id", "category", "priority", "reason", "flag"]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"Classified {len(results)} complaints.")
    if skipped:
        print(f"Skipped {len(skipped)} malformed rows (line numbers: {skipped})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UC-0A Complaint Classifier")
    parser.add_argument("--input",  required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    batch_classify(args.input, args.output)
    print(f"Done. Results written to {args.output}")
