# skills.md — UC-0A Complaint Classifier
# INSTRUCTIONS: Same as agents.md — paste README into AI, ask for skills.md YAML

skills:
  - name: classify_complaint
    description: "Classifies a single complaint row based on predefined rules."
    input: "one complaint row (dict with description, location fields)"
    output: "dict with category, priority, reason, flag"
    error_handling: "vague/short descriptions → Other + NEEDS_REVIEW"

  - name: batch_classify
    description: "Iterates through an input CSV and classifies all entries."
    input: "path to test CSV file"
    output: "path to results CSV file"
    error_handling: "malformed rows logged and skipped, processing continues"
