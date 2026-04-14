"""
UC-0A — Complaint Classifier
Implementation follows R.I.C.E (Role, Intent, Context, Enforcement) 
and CRAFT principles as defined in agents.md and skills.md.
"""
import argparse
import csv
import os
import sys

# --- SYSTEM PROMPT (From agents.md) ---
SYSTEM_PROMPT = """
Role: City Operations AI Complaint Classifier.
Boundary: Categorize municipal reports into the approved city taxonomy.

Allowed Categories: 
Pothole, Flooding, Streetlight, Waste, Noise, Road Damage, Heritage Damage, Heat Hazard, Drain Blockage, Other.

Enforcement Rules:
1. Category must be exactly one value from the allowed list. No variations.
2. Priority must be Urgent if description contains any severity keyword: injury, child, school, hospital, ambulance, fire, hazard, fell, collapse.
3. Every output row must include a reason field citing specific words from the description.
4. If category cannot be determined confidently — output category: Other and flag: NEEDS_REVIEW.
5. If description is vague or too short — output category: Other and flag: NEEDS_REVIEW.
6. Never invent category names outside the allowed list.

Output JSON Format for each row:
{
  "category": "Allowed Category Name",
  "priority": "Urgent/Standard/Low",
  "reason": "One sentence justification citing specific words",
  "flag": "NEEDS_REVIEW or (blank)"
}
"""

def classify_complaint(row: dict) -> dict:
    """
    Skill: classify_complaint
    Input: one complaint row (dict with description, location fields)
    Output: dict with category, priority, reason, flag
    Error handling: vague/short descriptions → Other + NEEDS_REVIEW
    """
    description = row.get("description", "").strip()
    location = row.get("location", "Unknown")
    
    # Heuristic Logic for Severity (Rule 2)
    severity_keywords = ["injury", "child", "school", "hospital", "ambulance", "fire", "hazard", "fell", "collapse"]
    priority = "Standard"
    desc_lower = description.lower()
    for kw in severity_keywords:
        if kw in desc_lower:
            priority = "Urgent"
            break

    # Error handling for vague/short descriptions (Rule 5)
    if len(description) < 15:
        return {
            "category": "Other",
            "priority": priority,
            "reason": f"Input too short ('{description}') to classify confidently.",
            "flag": "NEEDS_REVIEW"
        }

    # Taxonomy Mapping Logic (Ensuring Rules 1, 4, 6)
    category = "Other"
    reason = "No taxonomy keyword match."
    flag = "NEEDS_REVIEW"
    
    taxonomy_map = {
        "pothole": "Pothole",
        "flooding": "Flooding",
        "flood": "Flooding",
        "light": "Streetlight",
        "waste": "Waste",
        "garbage": "Waste",
        "noise": "Noise",
        "sound": "Noise",
        "road": "Road Damage",
        "heritage": "Heritage Damage",
        "statue": "Heritage Damage",
        "heat": "Heat Hazard",
        "drain": "Drain Blockage"
    }
    
    matches = [cat for kw, cat in taxonomy_map.items() if kw in desc_lower]
    unique_matches = sorted(list(set(matches)))

    # Ambiguity Check (Rule 4)
    if len(unique_matches) == 1:
        category = unique_matches[0]
        keyword = next(kw for kw in taxonomy_map.keys() if kw in desc_lower)
        # Reason citing words (Rule 3)
        reason = f"Detected '{keyword}' in description, mapping to {category}."
        flag = ""
    elif len(unique_matches) > 1:
        category = "Other"
        reason = f"Ambiguous input matching multiple categories: {list(unique_matches)}."
        flag = "NEEDS_REVIEW"
    else:
        category = "Other"
        reason = "No specific keywords found mapping to the current list of categories."
        flag = "NEEDS_REVIEW"

    # Final Enforcement of Allowed List
    allowed = ["Pothole", "Flooding", "Streetlight", "Waste", "Noise", "Road Damage", "Heritage Damage", "Heat Hazard", "Drain Blockage", "Other"]
    if category not in allowed:
        category = "Other"
        flag = "NEEDS_REVIEW"

    return {
        "category": category,
        "priority": priority,
        "reason": reason,
        "flag": flag
    }

def batch_classify(input_path: str, output_path: str):
    """
    Skill: batch_classify
    Input: path to test CSV file
    Output: path to results CSV file
    Error handling: malformed rows logged and skipped, processing continues
    """
    if not os.path.exists(input_path):
        print(f"Error: Input file '{input_path}' not found.")
        sys.exit(1)

    processed_data = []
    
    try:
        with open(input_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row_id, row in enumerate(reader, 1):
                try:
                    # Handle malformed/incomplete rows (Skill Error Handling)
                    if not row.get("description") or not row.get("location"):
                        print(f"Row {row_id}: Malformed/Empty description or location. Skipping...")
                        continue
                    
                    classification = classify_complaint(row)
                    
                    # Combine original fields with classification results
                    final_row = {**row, **classification}
                    processed_data.append(final_row)
                    
                except Exception as e:
                    print(f"Row {row_id}: Unexpected error processing. Logging and continuing... ({e})")
                    continue

    except Exception as e:
        print(f"Fatal error reading CSV: {e}")
        sys.exit(1)

    if not processed_data:
        print("No valid complaint rows to process.")
        return

    # Write Results to CSV
    try:
        fieldnames = list(processed_data[0].keys())
        with open(output_path, mode='w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(processed_data)
        print(f"Done. {len(processed_data)} complaints classified. Results saved to: {output_path}")
    except Exception as e:
        print(f"Error saving output file: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UC-0A Complaint Classifier Script")
    parser.add_argument("--input", required=True, help="Input CSV path (data/city-test-files/test_pune.csv)")
    parser.add_argument("--output", required=True, help="Output CSV path (uc-0a/results_pune.csv)")
    
    args = parser.parse_args()
    batch_classify(args.input, args.output)
