# skills.md — UC-0A Complaint Classifier
# INSTRUCTIONS: Same as agents.md — paste README into AI, ask for skills.md YAML

skills:
  - name: classify_complaint
    description: "Classifies a single complaint into category, priority, reason, and flag."
    input: "one complaint row (dict with description, location fields)"
    output: "dict with category, priority, reason, flag"
    error_handling: "vague/short descriptions → Other + NEEDS_REVIEW"

  - name: batch_classify
    description: "Processes a batch of complaints from a CSV file and outputs classifications to a new CSV file."
    input: "path to test CSV file"
    output: "path to results CSV file"
    error_handling: "malformed rows logged and skipped, processing continues"
