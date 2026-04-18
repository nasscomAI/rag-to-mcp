import argparse
import csv
import os

def classify_complaint(row: dict) -> dict:
    """
    Classify a single complaint row using heuristic logic (simulating AI behavior).
    """
    description = row.get("description", "").lower()
    complaint_id = row.get("complaint_id", "N/A")

    # 1. Allowed Categories & Keywords
    taxonomy = {
        "Pothole": ["pothole", "pit", "crater"],
        "Flooding": ["flood", "water", "rain", "overflow"],
        "Streetlight": ["light", "dark", "lamp", "bulb"],
        "Waste": ["garbage", "trash", "waste", "smell", "dump"],
        "Noise": ["loud", "music", "noise", "sound"],
        "Road Damage": ["road", "cracked", "sidewalk", "pavement"],
        "Heritage Damage": ["monument", "heritage", "old city", "statue"],
        "Heat Hazard": ["heat", "hot", "sun", "summer"],
        "Drain Blockage": ["drain", "sewage", "blocked", "gutter"],
    }

    # 2. Category Matching
    category = "Other"
    for cat, keywords in taxonomy.items():
        if any(kw in description for kw in keywords):
            category = cat
            break

    # 3. Severity & Priority
    severity_keywords = ["injury", "child", "school", "hospital", "ambulance", "fire", "hazard", "fell", "collapse"]
    priority = "Standard"
    found_keyword = None
    for kw in severity_keywords:
        if kw in description:
            priority = "Urgent"
            found_keyword = kw
            break

    # 4. Reason Generation
    if priority == "Urgent":
        reason = f"Urgent priority because the description mentions '{found_keyword}'."
    elif category != "Other":
        reason = f"Classified as {category} due to keywords in the description."
    else:
        reason = "Description is ambiguous or does not map to a standard category."

    # 5. Flagging
    flag = "NEEDS_REVIEW" if category == "Other" or not description else ""

    return {
        "complaint_id": complaint_id,
        "category": category,
        "priority": priority,
        "reason": reason,
        "flag": flag
    }

def batch_classify(input_path: str, output_path: str):
    """Read input CSV, classify each row, write results CSV."""
    if not os.path.exists(input_path):
        print(f"Error: {input_path} not found.")
        return

    results = []
    with open(input_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                classified = classify_complaint(row)
                results.append(classified)
            except Exception as e:
                print(f"Skipping malformed row: {e}")

    if not results:
        print("No results to write.")
        return

    fieldnames = results[0].keys()
    with open(output_path, mode='w', encoding='utf-8', newline='') as f:
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
