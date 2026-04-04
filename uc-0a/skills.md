# skills.md — UC-0A Complaint Classifier

skills:
  - name: classify_complaint
    description: >
      Classifies a single citizen complaint into a structured output
      using the fixed classification schema. Applies severity keyword
      detection for priority escalation and taxonomy enforcement for
      category assignment.
    input: >
      One complaint row as a dict with at minimum a description field
      and a location field.
    output: >
      A dict with four fields:
        category — one of: Pothole, Flooding, Streetlight, Waste, Noise,
                   Road Damage, Heritage Damage, Heat Hazard, Drain Blockage, Other
        priority — Urgent, Standard, or Low
        reason   — one sentence citing specific words from the description
        flag     — NEEDS_REVIEW or blank
    error_handling: >
      Vague, extremely short, or unintelligible descriptions produce
      category: Other, flag: NEEDS_REVIEW, and a reason stating the
      description was insufficient for confident classification.

  - name: batch_classify
    description: >
      Processes an entire test CSV file of complaints, applying
      classify_complaint to each row and writing results to an output CSV.
    input: >
      Path to a test CSV file (e.g., data/city-test-files/test_pune.csv).
    output: >
      Path to a results CSV file (e.g., uc-0a/results_pune.csv) containing
      all original columns plus category, priority, reason, and flag.
    error_handling: >
      Malformed or unreadable rows are logged with their row index and
      skipped. Processing continues for remaining rows. A summary of
      skipped rows is printed at the end.
