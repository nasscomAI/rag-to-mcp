skills:
  - name: classify_complaint
    description: Analyzes a single complaint description to determine its category, priority, and justification.
    input: A dictionary containing 'complaint_id' and 'description'.
    output: A dictionary with 'category', 'priority', 'reason', and 'flag'.
    error_handling: Handles empty or ambiguous descriptions by defaulting to 'Other' and flagging for review.

  - name: batch_classify
    description: Processes a CSV file of complaints and writes the classified results to a new CSV.
    input: Input CSV path and output CSV path.
    output: A CSV file with classification results.
    error_handling: Logs and skips malformed rows while ensuring the entire file is processed.
