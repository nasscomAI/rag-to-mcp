"""
UC-0A — Complaint Classifier
classifier.py — Starter file

Build this using your AI coding tool:
1. Share agents.md, skills.md, and uc-0a/README.md
2. Ask the AI to implement this file
3. Run: python3 classifier.py --input ../data/city-test-files/test_pune.csv \
                               --output results_pune.csv
"""
import argparse
import csv

CATEGORIES = [
    "Pothole", "Flooding", "Streetlight", "Waste", "Noise", "Road Damage", 
    "Heritage Damage", "Heat Hazard", "Drain Blockage", "Other"
]
SEVERITY_KEYWORDS = ["injury", "child", "school", "hospital", "ambulance", "fire", "hazard", "fell", "collapse"]

def classify_complaint(row: dict) -> dict:
    """
    Classify a single complaint row.
    Returns dict with: complaint_id, category, priority, reason, flag
    """
    desc = row.get("description", "").lower()
    
    # Priority check
    priority = "Standard"
    triggered_kws = []
    for kw in SEVERITY_KEYWORDS:
        if kw in desc:
            priority = "Urgent"
            triggered_kws.append(kw)
    
    # Category mapping & Ambiguity handling
    category = "Other"
    flag = ""
    reason_words = []
    
    if "pothole" in desc:
        category = "Pothole"
        reason_words.append("pothole")
    elif "flood" in desc or "rain" in desc:
        category = "Flooding"
        reason_words.append("flood/rain")
    elif "streetlight" in desc or "lights out" in desc:
        category = "Streetlight"
        reason_words.append("streetlight")
    elif "garbage" in desc or "waste" in desc or "animal" in desc:
        category = "Waste"
        reason_words.append("garbage/waste/animal")
    elif "music" in desc or "noise" in desc:
        category = "Noise"
        reason_words.append("music")
    elif "manhole" in desc or "surface" in desc or "broken" in desc:
        category = "Road Damage"
        reason_words.append("broken/surface")
    elif "drain" in desc:
        category = "Drain Blockage"
        reason_words.append("drain")
    elif "heritage" in desc:
        category = "Heritage Damage"
        reason_words.append("heritage")
    else:
        category = "Other"
        flag = "NEEDS_REVIEW"
        
    reason_words.extend(triggered_kws)
    
    # Reason field
    if reason_words:
        reason = f"Cites specific words from description: {', '.join(set(reason_words))}"
    else:
        reason = "No specific words matched. Ambiguous description."
        category = "Other"
        flag = "NEEDS_REVIEW"

    return {
        "complaint_id": row.get("complaint_id", ""),
        "category": category,
        "priority": priority,
        "reason": reason,
        "flag": flag
    }

def batch_classify(input_path: str, output_path: str):
    """Read input CSV, classify each row, write results CSV."""
    with open(input_path, mode="r", encoding="utf-8") as infile, \
         open(output_path, mode="w", encoding="utf-8", newline="") as outfile:
        
        reader = csv.DictReader(infile)
        fieldnames = ["complaint_id", "category", "priority", "reason", "flag"]
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for row in reader:
            try:
                if not row: continue
                result = classify_complaint(row)
                writer.writerow(result)
            except Exception as e:
                print(f"Skipping malformed row: {e}")
                continue

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UC-0A Complaint Classifier")
    parser.add_argument("--input",  required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    batch_classify(args.input, args.output)
    print(f"Done. Results written to {args.output}")
