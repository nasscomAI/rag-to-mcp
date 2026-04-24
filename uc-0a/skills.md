skills:
  - name: classify_complaint
    description: "Reads a single complaint and classifies it according to the predefined schema and enforcement rules, preventing taxonomy drift, severity blindness, missing justification, and hallucinated sub-categories."
    input: "One complaint row (dict with description, location fields)"
    output: "Dict with category, priority, reason, flag"
    error_handling: "If the description is vague/short, or if ambiguity causes false confidence, it must fall back to outputting `category: Other` and `flag: NEEDS_REVIEW`."

  - name: batch_classify
    description: "Reads a CSV file containing multiple complaints, applies the classify_complaint skill to each row, and writes the results to a specified output CSV file."
    input: "Path to test CSV file"
    output: "Path to results CSV file"
    error_handling: "If malformed rows are encountered, they must be logged and skipped, allowing processing of the remaining rows to continue."
