# skills.md — UC-0A Complaint Classifier

skills:
  - name: classify_complaint
    description: >
      Classify a single citizen complaint into a structured output matching
      the fixed schema. Applies the category enum, severity keyword scan,
      and ambiguity refusal rules defined in agents.md enforcement section.
    input: >
      One complaint row as a dict with keys: complaint_id, date_raised,
      city, ward, location, description, reported_by, days_open.
      The 'description' field is the primary text used for classification.
    output: >
      A dict with exactly four fields:
        - category: one of Pothole, Flooding, Streetlight, Waste, Noise,
          Road Damage, Heritage Damage, Heat Hazard, Drain Blockage, Other.
        - priority: "Urgent" if any severity keyword (injury, child, school,
          hospital, ambulance, fire, hazard, fell, collapse) is found
          case-insensitively in the description; "Standard" for actionable
          complaints; "Low" for informational-only.
        - reason: exactly one sentence citing specific words from the
          complaint description. Never blank, never fabricated.
        - flag: "NEEDS_REVIEW" if the complaint is vague, too short
          (fewer than 5 meaningful words), or does not clearly map to a
          single category. Otherwise blank.
    error_handling: >
      If description is missing, empty, or fewer than 5 meaningful words,
      return category "Other", priority "Low", flag "NEEDS_REVIEW", and
      reason "Description too vague or short for confident classification."
      Never raise an exception for a single malformed row.

  - name: batch_classify
    description: >
      Read an input CSV of citizen complaints, classify every row using
      classify_complaint, and write a results CSV. Ensures end-to-end
      processing even when individual rows are malformed.
    input: >
      Path to a CSV file containing complaint rows with headers:
      complaint_id, date_raised, city, ward, location, description,
      reported_by, days_open.
    output: >
      Path to a results CSV file with headers: complaint_id, category,
      priority, reason, flag. One output row per valid input row.
    error_handling: >
      Malformed or unreadable rows are logged to stderr with the row index
      and error message, then skipped. Processing continues for all
      remaining rows. If the input file cannot be opened, raise a
      FileNotFoundError with a clear message. The results CSV is written
      only after all rows are processed.
