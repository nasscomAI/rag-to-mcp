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
import json
import os
import time
import google.generativeai as genai

# Configure Gemini
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

system_instruction = """You are an AI complaint classifier for the City Operations team.
Read each complaint and accurately output a category, priority, reason, and flag to feed the Director's dashboard.
The City Operations team receives hundreds of complaints weekly. Accurate classification ensures urgent issues involving children, injuries, or hazards are prioritized appropriately. A naive prompt previously resulted in taxonomy drift, severity blindness, missing justifications, hallucinated sub-categories, and false confidence on ambiguous inputs.

Enforcement Rules:
- Category must be exactly one value from the allowed list: Pothole, Flooding, Streetlight, Waste, Noise, Road Damage, Heritage Damage, Heat Hazard, Drain Blockage, Other. No variations.
- Priority must be exactly one value from the allowed list: Urgent, Standard, Low. No variations.
- Priority must be Urgent if description contains any severity keyword: injury, child, school, hospital, ambulance, fire, hazard, fell, collapse.
- Every output row must include a reason field citing specific words from the description.
- If category cannot be determined confidently — output category: Other and flag: NEEDS_REVIEW.
- Never invent category names outside the allowed list."""

model = genai.GenerativeModel(
    'gemini-2.5-flash',
    system_instruction=system_instruction,
    generation_config={"response_mime_type": "application/json"}
)

def classify_complaint(row: dict) -> dict:
    """
    Classify a single complaint row.
    Returns dict with: complaint_id, category, priority, reason, flag
    """
    description = row.get("description", "")
    
    # Handle vague/short descriptions
    if len(description.split()) < 3:
        return {
            "complaint_id": row.get("complaint_id", ""),
            "category": "Other",
            "priority": "Standard",
            "reason": "Description is too short or vague.",
            "flag": "NEEDS_REVIEW"
        }
    
    prompt = f"Complaint Description: {description}\nLocation: {row.get('location', '')}\n\nOutput JSON with keys: category, priority, reason, flag."
    
    for attempt in range(3):
        try:
            response = model.generate_content(prompt)
            result = json.loads(response.text)
            result["complaint_id"] = row.get("complaint_id", "")
            
            # Ensure all required keys exist
            for key in ["category", "priority", "reason", "flag"]:
                if key not in result:
                    result[key] = ""
                    
            return result
        except Exception as e:
            if "429" in str(e):
                print(f"Rate limit hit. Retrying in 15 seconds...")
                time.sleep(15)
                continue
            return {
                "complaint_id": row.get("complaint_id", ""),
                "category": "Other",
                "priority": "Standard",
                "reason": f"Error parsing response: {str(e)}",
                "flag": "NEEDS_REVIEW"
            }
            
    return {
        "complaint_id": row.get("complaint_id", ""),
        "category": "Other",
        "priority": "Standard",
        "reason": "Failed after retries due to rate limiting.",
        "flag": "NEEDS_REVIEW"
    }

def batch_classify(input_path: str, output_path: str):
    """Read input CSV, classify each row, write results CSV."""
    results = []
    
    try:
        with open(input_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    classification = classify_complaint(row)
                    results.append(classification)
                    time.sleep(2)  # basic rate limit spacing
                except Exception as e:
                    print(f"Skipping malformed row {row.get('complaint_id', 'unknown')}: {e}")
                    continue
    except Exception as e:
        print(f"Error reading {input_path}: {e}")
        return
        
    if not results:
        print("No results to write.")
        return
        
    fieldnames = ["complaint_id", "category", "priority", "reason", "flag"]
    
    try:
        with open(output_path, mode='w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for res in results:
                writer.writerow(res)
    except Exception as e:
        print(f"Error writing {output_path}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UC-0A Complaint Classifier")
    parser.add_argument("--input",  required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    batch_classify(args.input, args.output)
    print(f"Done. Results written to {args.output}")
