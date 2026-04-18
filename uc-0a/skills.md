# skills.md — UC-0A Complaint Classifier

skills:
  - name: classify_complaint
    description: "Classify a single complaint row using RICE enforcement rules. Takes description and location, outputs category, priority, reason, and flag."
    input: |
      {
        "complaint_id": "string",
        "description": "string (complaint text)",
        "location": "string (optional)"
      }
    output: |
      {
        "complaint_id": "string",
        "category": "string (one of Pothole|Flooding|Streetlight|Waste|Noise|Road Damage|Heritage Damage|Heat Hazard|Drain Blockage|Other)",
        "priority": "string (Urgent|Standard|Low)",
        "reason": "string (one sentence citing specific words from description)",
        "flag": "string (NEEDS_REVIEW or empty)"
      }
    error_handling: "Vague/short/ambiguous descriptions → output category: Other, flag: NEEDS_REVIEW. Never fail; always produce output."

  - name: batch_classify
    description: "Read a test CSV file, classify each row using classify_complaint skill, write results to output CSV with all required fields."
    input: |
      {
        "input_path": "string (path to test_[city].csv)",
        "output_path": "string (path to results_[city].csv)"
      }
    output: |
      {
        "output_path": "string (path to written results CSV)",
        "rows_processed": "integer",
        "rows_skipped": "integer"
      }
    error_handling: "Malformed rows logged and skipped. Processing continues. No row failure should stop batch. All errors logged to console with row number and reason."
