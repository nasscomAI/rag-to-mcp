skills:
  - name: classify_complaint
    description: >
      Analyzes a single municipal complaint and assigns city-approved category, 
      priority, citation-based reason, and an ambiguity flag.
    input: dict with 'description' and 'location' fields
    output: dict with 'category', 'priority', 'reason', and 'flag'
    error_handling: >
      Vague or extremely short descriptions are assigned 'category: Other' 
      and 'flag: NEEDS_REVIEW' to prevent false confidence. 
      Strict taxonomy enforcement avoids taxonomy drift by using only the 10 allowed categories.
  - name: batch_classify
    description: >
      Processes a CSV file containing multiple complaints and exports the results 
      into a new CSV file for the Director's dashboard.
    input: path to input test CSV file (e.g., ../data/city-test-files/test_pune.csv)
    output: path to target results CSV file (e.g., results_pune.csv)
    error_handling: >
      Malformed or incomplete rows are logged and skipped, ensuring the batch 
      processing continues for the remaining valid rows.
