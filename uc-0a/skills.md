# skills.md — UC-0A Complaint Classifier

skills:
  - name: classify_complaint
    description: "Classifies a single citizen complaint into category, priority, reason, and flag using the approved schema and enforcement rules."
    input: "A complaint row as a dict with at least a description field and optional location fields."
    output: "A dict with four fields: category (one value from the allowed list), priority (Urgent / Standard / Low), reason (one sentence citing specific words from the description), flag (NEEDS_REVIEW or blank)."
    error_handling: "If the description is vague, too short to classify confidently, or matches no known category, return category: Other and flag: NEEDS_REVIEW. Do not guess."

  - name: batch_classify
    description: "Reads a CSV file of complaints, runs classify_complaint on each row, and writes results to an output CSV file."
    input: "Path to a city test CSV file (e.g. ../data/city-test-files/test_pune.csv)."
    output: "Path to a results CSV file (e.g. results_pune.csv) containing all original fields plus category, priority, reason, and flag columns."
    error_handling: "Malformed or unparseable rows are logged with their row number and skipped; processing continues for all remaining rows."
