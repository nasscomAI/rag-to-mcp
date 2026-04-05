import argparse
import csv
import sys

ALLOWED_CATEGORIES = {
    "Pothole", "Flooding", "Streetlight", "Waste", "Noise", 
    "Road Damage", "Heritage Damage", "Heat Hazard", "Drain Blockage", "Other"
}

SEVERITY_KEYWORDS = {
    "injury", "child", "school", "hospital", "ambulance", 
    "fire", "hazard", "fell", "collapse"
}


def classify_complaint(row: dict) -> dict:
    """
    RICE Encapsulation: Strict taxonomic bounds without hallucination.
    Returns identically structured objects.
    """
    description = row.get("description", "").strip()
    desc_lower = description.lower()
    
    output = {
        "complaint_id": row.get("complaint_id", "UNKNOWN"),
        "category": "Other",
        "priority": "Low", # Defaulting to lowest if standard isn't pushed
        "reason": "",
        "flag": ""
    }
    
    # 1. Error Handling Boundary
    if len(description) < 15:
        output["flag"] = "NEEDS_REVIEW"
        output["reason"] = f"Flagged ambiguous logic due to short vague textual input: '{description}'"
        return output
        
    # 2. Enforcement: Priority Escalation via Deterministic Keywords (Severity Blindness fix)
    urgent_triggers = [kw for kw in SEVERITY_KEYWORDS if kw in desc_lower]
    if urgent_triggers:
        output["priority"] = "Urgent"
        output["reason"] += f"Escalated priority aggressively because the text cited dangers: {', '.join(urgent_triggers)}. "
    else:
        output["priority"] = "Standard"
        
    # 3. Enforcement: Bounded Schema Generation (Taxonomy Drift & Hallucination fix)
    category_assigned = False
    
    # Rigid matching structure preventing string variations
    mapping_keywords = {
        "pothole": "Pothole",
        "flood": "Flooding", "water": "Flooding", "drain": "Drain Blockage",
        "light": "Streetlight", "dark": "Streetlight",
        "waste": "Waste", "garbage": "Waste", "trash": "Waste",
        "noise": "Noise", "loud": "Noise",
        "road": "Road Damage", "crack": "Road Damage",
        "heritage": "Heritage Damage", "monument": "Heritage Damage",
        "heat": "Heat Hazard"
    }
    
    for kw, exact_cat in mapping_keywords.items():
        if kw in desc_lower:
            output["category"] = exact_cat
            # Output rule: Force justification citation
            output["reason"] += f"Explicitly mapped to category {exact_cat} because raw description contained '{kw}'."
            category_assigned = True
            break
            
    # 4. Enforcement: Ambiguity requires defensive degradation (False Confidence fix)
    if not category_assigned:
        output["category"] = "Other"
        output["flag"] = "NEEDS_REVIEW"
        output["reason"] += "Routed to Other + Review queue due to lacking confident mapped classifier elements."
        
    return output


def batch_classify(input_path: str, output_path: str):
    """
    Orchestrates robust queue management without crushing the job on bad inputs.
    """
    processed_count = 0
    results = []
    
    try:
        with open(input_path, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            
            for idx, row in enumerate(reader, start=1):
                # Enforce batch_classify error handling skipping malformed datasets cleanly
                if not row or "description" not in row:
                    print(f"⚠️ [Error Handle] Logger dropping corrupted iteration at row limit #{idx}. Bypassing safely...")
                    continue
                
                classified = classify_complaint(row)
                results.append(classified)
                processed_count += 1
                
    except FileNotFoundError:
        print(f"Critical Halt: File exactly matching '{input_path}' not situated.")
        sys.exit(1)
        
    if not results:
        print("Empty extraction buffer.")
        sys.exit(0)
        
    # Write cleanly exactly mapping the Dict
    fields = ["complaint_id", "category", "priority", "reason", "flag"]
    with open(output_path, mode='w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(results)
        
    print(f"Classification success: Processed {processed_count} rows firmly inside strict Taxonomy rules.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UC-0A Formal Classifier Endpoint")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    
    batch_classify(args.input, args.output)
    print(f"Done. Extracted to -> {args.output}")
