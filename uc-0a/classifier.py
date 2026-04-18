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
import re

SEVERITY_KEYWORDS = {"injury", "child", "school", "hospital", "ambulance", "fire", "hazard", "fell", "collapse"}
ALLOWED_CATEGORIES = {
    "Pothole": ["pothole", "crater"],
    "Flooding": ["flood", "water", "inundated"],
    "Streetlight": ["light", "lamp", "dark"],
    "Waste": ["waste", "trash", "garbage", "rubbish"],
    "Noise": ["noise", "loud", "sound"],
    "Road Damage": ["road", "crack", "surface"],
    "Heritage Damage": ["heritage", "monument"],
    "Heat Hazard": ["heat", "sun"],
    "Drain Blockage": ["drain", "clog", "blockage", "sewer"],
}

def classify_complaint(row: dict) -> dict:
    """
    Classify a single complaint row.
    Returns dict with: complaint_id, category, priority, reason, flag
    """
    description = row.get("description", "").lower()
    
    # Error handling for short/vague
    if len(description.split()) < 5:
        return {
            "complaint_id": row.get("complaint_id"),
            "category": "Other",
            "priority": "Standard",
            "reason": "Description is too short or vague.",
            "flag": "NEEDS_REVIEW"
        }
        
    # Check Severity
    is_urgent = False
    priority = "Standard"
    for kw in SEVERITY_KEYWORDS:
        if kw in description:
            is_urgent = True
            priority = "Urgent"
            break
            
    # Check Category
    category = "Other"
    for cat, aliases in ALLOWED_CATEGORIES.items():
        if any(alias in description for alias in aliases):
            category = cat
            break
            
    flag = "NEEDS_REVIEW" if category == "Other" else ""
    
    # Reason
    sentences = re.split(r'(?<=[.!?])\s+', row.get("description", "").strip())
    reason_sentence = sentences[0] if sentences else row.get("description")
    if is_urgent:
        for s in sentences:
            if any(kw in s.lower() for kw in SEVERITY_KEYWORDS):
                reason_sentence = s.strip()
                break
    elif category != "Other":
        for s in sentences:
            if any(kw in s.lower() for kw in ALLOWED_CATEGORIES[category]):
                reason_sentence = s.strip()
                break
                
    return {
        "complaint_id": row.get("complaint_id"),
        "category": category,
        "priority": priority,
        "reason": reason_sentence,
        "flag": flag
    }

def batch_classify(input_path: str, output_path: str):
    """Read input CSV, classify each row, write results CSV."""
    with open(input_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        
    results = []
    fieldnames = ["complaint_id", "category", "priority", "reason", "flag"]
    for i, row in enumerate(rows):
        try:
            res = classify_complaint(row)
            results.append(res)
        except Exception as e:
            print(f"Skipping malformed row {i}: {e}")
            
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UC-0A Complaint Classifier")
    parser.add_argument("--input",  required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    batch_classify(args.input, args.output)
    print(f"Done. Results written to {args.output}")
