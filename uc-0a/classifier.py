import argparse
import csv
import os
import json
import time

def call_llm(prompt: str) -> str:
    """Uses Gemini API to classify the complaint based on the prompt."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return json.dumps({
            "category": "Other",
            "priority": "Standard",
            "reason": "[ERROR] GEMINI_API_KEY not set",
            "flag": "NEEDS_REVIEW"
        })
        
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        # We request JSON response from Gemini
        model = genai.GenerativeModel(
            "gemini-1.5-flash", 
            generation_config={"response_mime_type": "application/json"}
        )
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return json.dumps({
            "category": "Other",
            "priority": "Standard",
            "reason": f"[ERROR] LLM Call failed: {str(e)}",
            "flag": "NEEDS_REVIEW"
        })

def classify_complaint(row: dict, agents_text: str, skills_text: str) -> dict:
    """
    Classify a single complaint row.
    Returns dict with: complaint_id, category, priority, reason, flag
    """
    description = row.get('description', '')
    location = row.get('location', '')
    
    # Error handling: vague/short descriptions -> Other + NEEDS_REVIEW
    if not description or len(description.strip()) < 5:
        return {
            "complaint_id": row.get('complaint_id', ''),
            "category": "Other",
            "priority": "Standard",
            "reason": "Vague or short description",
            "flag": "NEEDS_REVIEW"
        }

    prompt = f"""You are the AI Complaint Classifier.

=== AGENTS DEFINITION ===
{agents_text}

=== SKILLS DEFINITION ===
{skills_text}

=== INPUT COMPLAINT ===
Location: {location}
Description: {description}

=== INSTRUCTIONS ===
Classify the complaint according to the schema and enforcement rules above.
Output strictly valid JSON with exactly the following keys:
"category", "priority", "reason", "flag"
"""

    response_text = call_llm(prompt)
    
    try:
        result = json.loads(response_text)
        result["complaint_id"] = row.get("complaint_id", "")
        return result
    except Exception as e:
        return {
            "complaint_id": row.get('complaint_id', ''),
            "category": "Other",
            "priority": "Standard",
            "reason": f"Parsing failed: {str(e)}",
            "flag": "NEEDS_REVIEW"
        }

def batch_classify(input_path: str, output_path: str):
    """Read input CSV, classify each row, write results CSV."""
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    try:
        with open(os.path.join(base_dir, 'agents.md'), 'r', encoding='utf-8') as f:
            agents_text = f.read()
        with open(os.path.join(base_dir, 'skills.md'), 'r', encoding='utf-8') as f:
            skills_text = f.read()
    except FileNotFoundError:
        print("Error: agents.md or skills.md not found. Ensure they are in the same directory.")
        return

    results = []
    
    with open(input_path, mode='r', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            complaint_id = row.get('complaint_id')
            # Error handling: malformed rows logged and skipped, processing continues
            if not complaint_id:
                print("Skipping malformed row missing complaint_id.")
                continue
                
            print(f"Classifying {complaint_id}...")
            result_dict = classify_complaint(row, agents_text, skills_text)
            
            clean_result = {
                "complaint_id": result_dict.get("complaint_id", ""),
                "category": result_dict.get("category", "Other"),
                "priority": result_dict.get("priority", "Standard"),
                "reason": result_dict.get("reason", "No reason provided"),
                "flag": result_dict.get("flag", "")
            }
            results.append(clean_result)
            
            # Minimal sleep to avoid Gemini rate limits on the free tier
            time.sleep(1.0)
            
    if not results:
        print("No results to write.")
        return
        
    with open(output_path, mode='w', encoding='utf-8', newline='') as outfile:
        fieldnames = ["complaint_id", "category", "priority", "reason", "flag"]
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UC-0A Complaint Classifier")
    parser.add_argument("--input",  required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    batch_classify(args.input, args.output)
    print(f"Done. Results written to {args.output}")
