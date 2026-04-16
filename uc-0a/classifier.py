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
import sys
import re

ALLOWED_CATEGORIES = {
    "Pothole", "Flooding", "Streetlight", "Waste", "Noise", 
    "Road Damage", "Heritage Damage", "Heat Hazard", "Drain Blockage", "Other"
}

SEVERITY_KEYWORDS = ["injury", "child", "school", "hospital", "ambulance", "fire", "hazard", "fell", "collapse"]

CATEGORY_KEYWORDS = {
    "Pothole": ["pothole", "crater"],
    "Flooding": ["flood", "waterlog", "water logged"],
    "Streetlight": ["street light", "streetlight", "dark", "no light"],
    "Waste": ["garbage", "waste", "trash", "rubbish"],
    "Noise": ["noise", "loud", "music", "party", "sound"],
    "Road Damage": ["crack", "road damage", "broken road", "sinkhole"],
    "Heritage Damage": ["heritage", "monument", "statue", "ruins"],
    "Heat Hazard": ["heat", "sun", "blazing", "heatwave"],
    "Drain Blockage": ["drain", "clog", "choke", "blockage"],
}

def classify_complaint(row: dict) -> dict:
    """
    Classify a single complaint row based on enforcement rules.
    Returns dict with: complaint_id, category, priority, reason, flag
    """
    description = row.get("description", "").lower()
    
    # Error handling: vague/short descriptions
    if len(description.split()) < 3:
        return {
            "complaint_id": row.get("complaint_id", row.get("id", "")),
            "category": "Other",
            "priority": "Low",
            "reason": "Vague or very short description.",
            "flag": "NEEDS_REVIEW"
        }

    priority = "Standard"
    reason_words = []
    
    # Priority enforcement rule
    for kw in SEVERITY_KEYWORDS:
        if re.search(r'\b' + kw + r'\b', description):
            priority = "Urgent"
            reason_words.append(kw)
            
    # Category enforcement rule
    category = "Other"
    found_categories = set()
    for cat, kws in CATEGORY_KEYWORDS.items():
        for kw in kws:
            if re.search(r'\b' + kw + r'\b', description):
                found_categories.add(cat)
                reason_words.append(kw)
                
    if len(found_categories) == 1:
        category = list(found_categories)[0]
    
    # Ambiguity refusal rule
    flag = ""
    if category == "Other" or len(found_categories) > 1:
        category = "Other"
        flag = "NEEDS_REVIEW"
        
    reason_text = "Found relevant keywords: " + ", ".join(set(reason_words)) if reason_words else "No specific keywords mapped."

    return {
        "complaint_id": row.get("complaint_id", row.get("id", "")),
        "category": category,
        "priority": priority,
        "reason": reason_text,
        "flag": flag
    }

def batch_classify(input_path: str, output_path: str):
    """Read input CSV, classify each row, write results CSV."""
    results = []
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            # Find ID column
            id_col = None
            if reader.fieldnames:
                for col in reader.fieldnames:
                    if "id" in col.lower():
                        id_col = col
                        break
            
            for row in reader:
                try:
                    # Malformed rows logging and skipping
                    if not row.get('description'):
                        print(f"Skipping malformed row: {row}")
                        continue
                        
                    res = classify_complaint(row)
                    # Use the correct original ID column if available
                    if id_col:
                        res["complaint_id"] = row.get(id_col, "")
                    results.append(res)
                except Exception as e:
                    print(f"Error processing row {row}: {e}")
                    continue
    except FileNotFoundError:
        print(f"Input file not found: {input_path}")
        sys.exit(1)

    if not results:
        print("No valid rows processed.")
        return

    fieldnames = ["complaint_id", "category", "priority", "reason", "flag"]
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UC-0A Complaint Classifier")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    batch_classify(args.input, args.output)
    print(f"Done. Results written to {args.output}")
