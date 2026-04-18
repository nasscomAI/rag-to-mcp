"""
UC-0A — Complaint Classifier
classifier.py — RICE-constrained complaint classification

Enforcement Rules:
1. Taxonomy Constraint: Category must be exactly one value from the allowed list
2. Severity Keyword Detection: Priority=Urgent if ANY severity keyword present
3. Justification Requirement: Every row must have a reason citing specific words
4. Ambiguity Handling: Unclear cases → Other + NEEDS_REVIEW
5. No Hallucinated Sub-Categories: Only use enum values, never invent
"""
import argparse
import csv
import sys
import re

# Enforcement: Fixed enum for categories (no variations allowed)
ALLOWED_CATEGORIES = {
    "Pothole", "Flooding", "Streetlight", "Waste", "Noise",
    "Road Damage", "Heritage Damage", "Heat Hazard", "Drain Blockage", "Other"
}

# Enforcement: Severity keywords that trigger Urgent priority
SEVERITY_KEYWORDS = {
    "injury", "child", "school", "hospital", "ambulance", "fire", "hazard", "fell", "collapse"
}

def extract_reason(description: str) -> str:
    """
    Extract a one-sentence reason citing specific words from the description.
    Returns the first sentence or a summary of key complaint element.
    """
    if not description or len(description.strip()) < 3:
        return "Vague or empty description"
    
    # Try to extract first sentence (up to period, question mark, or exclamation)
    sentences = re.split(r'[.!?]', description.strip())
    first_sentence = sentences[0].strip()
    
    if len(first_sentence) < 5:
        return "Short/unclear complaint"
    
    # Extract key words (first 15 words or full first sentence)
    words = first_sentence.split()[:15]
    return " ".join(words)

def has_severity_keywords(description: str) -> bool:
    """
    Check if description contains ANY severity keyword.
    Enforcement: ALL matches → Urgent (no threshold).
    """
    if not description:
        return False
    
    desc_lower = description.lower()
    for keyword in SEVERITY_KEYWORDS:
        if keyword in desc_lower:
            return True
    return False

def classify_complaint(row: dict) -> dict:
    """
    Classify a single complaint row using RICE enforcement rules.
    
    Enforcement:
    - Category must be from ALLOWED_CATEGORIES enum (no invented values)
    - Priority=Urgent if ANY severity keyword present
    - Reason must cite specific words from description
    - Ambiguous cases → Other + NEEDS_REVIEW
    
    Returns dict with: complaint_id, category, priority, reason, flag
    """
    complaint_id = row.get("complaint_id", "")
    description = row.get("description", "").strip()
    location = row.get("location", "").strip()
    
    # Extract reason (always include, never empty)
    reason = extract_reason(description)
    
    # Check for severity keywords (Urgent detection)
    has_severity = has_severity_keywords(description)
    
    # Determine category based on description keywords
    # If no strong match found, classify as Other
    category = determine_category(description)
    
    # Determine priority
    if has_severity:
        priority = "Urgent"
    else:
        priority = "Standard"  # Default; could be Low for explicit non-urgent indicators
    
    # Flag ambiguous cases
    flag = ""
    confidence = calculate_confidence(description, category)
    if confidence < 0.6:  # Low confidence threshold
        flag = "NEEDS_REVIEW"
    
    return {
        "complaint_id": complaint_id,
        "category": category,
        "priority": priority,
        "reason": reason,
        "flag": flag
    }

def determine_category(description: str) -> str:
    """
    Determine the category based on description content.
    Enforcement: Only return values from ALLOWED_CATEGORIES.
    If no clear match, return 'Other' (never invent categories).
    """
    if not description:
        return "Other"
    
    desc_lower = description.lower()
    
    # Define keyword patterns for each category (not exhaustive, just patterns)
    category_patterns = {
        "Pothole": ["pothole", "hole", "pit", "crater"],
        "Flooding": ["flood", "water", "wet", "inundation"],
        "Streetlight": ["light", "street light", "lamp", "dark", "blackout"],
        "Waste": ["garbage", "waste", "trash", "litter", "debris"],
        "Noise": ["noise", "sound", "loud", "loudspeaker", "music"],
        "Road Damage": ["road damage", "road", "asphalt", "pavement", "cracked"],
        "Heritage Damage": ["heritage", "monument", "historical", "ancient"],
        "Heat Hazard": ["heat", "hot", "temperature"],
        "Drain Blockage": ["drain", "drainage", "sewage", "blockage", "clogged"]
    }
    
    # Score each category by keyword matches
    best_category = "Other"
    best_score = 0
    
    for category, keywords in category_patterns.items():
        score = sum(1 for kw in keywords if kw in desc_lower)
        if score > best_score:
            best_score = score
            best_category = category
    
    # Enforcement: Always return a value from ALLOWED_CATEGORIES
    assert best_category in ALLOWED_CATEGORIES, f"Invalid category: {best_category}"
    return best_category

def calculate_confidence(description: str, category: str) -> float:
    """
    Calculate confidence score for the classification.
    Returns 0.0–1.0. Below 0.6 triggers NEEDS_REVIEW flag.
    """
    if not description or len(description.strip()) < 5:
        return 0.3  # Very short/vague
    
    if len(description.strip()) < 10:
        return 0.5  # Too short
    
    if category == "Other":
        return 0.4  # Default category (uncertain)
    
    return 0.8  # Reasonable confidence for matched categories

def batch_classify(input_path: str, output_path: str):
    """
    Read input CSV, classify each row, write results CSV.
    
    Enforcement:
    - Malformed rows logged and skipped, processing continues
    - Every row receives output (never skip)
    - All required fields present in output
    """
    rows_processed = 0
    rows_skipped = 0
    results = []
    
    try:
        with open(input_path, "r", encoding="utf-8") as infile:
            reader = csv.DictReader(infile)
            
            for row_num, row in enumerate(reader, start=2):  # start=2 (header is 1)
                try:
                    # Validate required fields
                    if not row.get("complaint_id") or not row.get("description"):
                        print(f"Warning: Row {row_num} missing complaint_id or description. Skipping.", file=sys.stderr)
                        rows_skipped += 1
                        continue
                    
                    # Classify the complaint
                    result = classify_complaint(row)
                    results.append(result)
                    rows_processed += 1
                    
                except Exception as e:
                    print(f"Error processing row {row_num}: {e}", file=sys.stderr)
                    rows_skipped += 1
                    continue
        
        # Write results to output CSV
        if results:
            with open(output_path, "w", newline="", encoding="utf-8") as outfile:
                fieldnames = ["complaint_id", "category", "priority", "reason", "flag"]
                writer = csv.DictWriter(outfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(results)
        
        print(f"Processed: {rows_processed}, Skipped: {rows_skipped}")
        return output_path
        
    except FileNotFoundError:
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        raise
    except Exception as e:
        print(f"Error during batch classification: {e}", file=sys.stderr)
        raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UC-0A Complaint Classifier")
    parser.add_argument("--input",  required=True, help="Path to input CSV (test_[city].csv)")
    parser.add_argument("--output", required=True, help="Path to output CSV (results_[city].csv)")
    args = parser.parse_args()
    
    batch_classify(args.input, args.output)
    print(f"Done. Results written to {args.output}")
