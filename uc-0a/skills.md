# skills.md — UC-0A Complaint Classifier
# INSTRUCTIONS: Same as agents.md — paste README into AI, ask for skills.md YAML

skills:
  - name: classify_complaint
    description: "Reads a single citizen complaint and outputs a category, priority, reason, and flag according to the classification schema."
    input: "One complaint row (dict with description, location fields)"
    output: "Dictionary with category, priority, reason, flag"
    error_handling: "If description is vague or short, output category as Other and flag as NEEDS_REVIEW"

  - name: batch_classify
    description: "Reads a batch of complaints from an input CSV file, applies classification to each row, and writes the output to a results CSV file."
    input: "Path to test CSV file"
    output: "Path to results CSV file"
    error_handling: "Malformed rows are logged and skipped, processing continues"
