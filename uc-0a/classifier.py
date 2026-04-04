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
import argparse
import csv
import os

def classify_complaint(row: dict) -> dict:
    """
    Classify a single complaint row using rule-based heuristics 
    to strictly adhere to the agents.md schema.
    Returns dict with: complaint_id, category, priority, reason, flag
    """
    desc = row.get('description', '').lower()
    
    # Enforcement 2: Severity keywords -> Urgent
    severity_keywords = ["injury", "child", "school", "hospital", "ambulance", "fire", "hazard", "fell", "collapse"]
    is_urgent = any(word in desc for word in severity_keywords)
    priority = "Urgent" if is_urgent else "Standard"

    # Enforcement 1 & 5: Exact categories mapping
    category_map = {
        "pothole": "Pothole",
        "flood": "Flooding",
        "streetlight": "Streetlight",
        "light": "Streetlight",
        "garbage": "Waste",
        "waste": "Waste",
        "music": "Noise",
        "noise": "Noise",
        "crack": "Road Damage",
        "surface": "Road Damage",
        "tile": "Road Damage",
        "heritage": "Heritage Damage",
        "heat": "Heat Hazard",
        "drain": "Drain Blockage",
        "manhole": "Drain Blockage"
    }

    category = "Other"
    found_keyword = None
    for kw, cat in category_map.items():
        if kw in desc:
            category = cat
            found_keyword = kw
            break
            
    # Enforcement 4: Ambiguity -> Other + NEEDS_REVIEW
    if category == "Other":
        flag = "NEEDS_REVIEW"
        reason = "The description provided was ambiguous and could not be confidently mapped to a specific category."
    else:
        flag = ""
        # Enforcement 3: Cite specific words
        reason = f"The description mentions '{found_keyword}' which classifies it under {category}."
        if is_urgent:
            reason += " Escalated to Urgent due to severity keywords."

    return {
        "complaint_id": row.get("complaint_id", ""),
        "category": category,
        "priority": priority,
        "reason": reason,
        "flag": flag
    }

def batch_classify(input_path: str, output_path: str):
    """Read input CSV, classify each row, write results CSV."""
    fieldnames = ['complaint_id', 'category', 'priority', 'reason', 'flag']
    
    with open(input_path, mode='r', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        rows = list(reader)
        
    results = []
    for i, row in enumerate(rows):
        print(f"Classifying {i+1}/{len(rows)}: ID {row.get('complaint_id', 'Unknown')}")
        classification = classify_complaint(row)
        results.append(classification)

    if os.path.dirname(output_path):
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
    with open(output_path, mode='w', newline='', encoding='utf-8') as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        for res in results:
            writer.writerow(res)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UC-0A Complaint Classifier")
    parser.add_argument("--input",  required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    batch_classify(args.input, args.output)
    print(f"Done. Results written to {args.output}")
