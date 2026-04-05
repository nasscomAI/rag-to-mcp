skills:
  - name: classify_complaint
    description: Processes an individual raw complaint record to securely categorize, prioritize, and flag issues according to strict operational taxonomies.
    input: A dictionary representing a single complaint row, specifically utilizing the 'description' and 'location' fields.
    output: A dictionary formally mapping exactly four strings—category, priority, reason, and flag.
    error_handling: Securely handles short, unparsable, or ambiguous inputs by forcefully degrading to outputting 'Other' for the category while triggering the 'NEEDS_REVIEW' flag, rather than attempting to hallucinate confident classifications.

  - name: batch_classify
    description: Handles bulk processing of CSV files automatically, routing rows concurrently to the unified classifier without crashing memory buffers.
    input: A string referencing the filesystem path to the test CSV file.
    output: A string confirming the path to the newly generated and populated results CSV file.
    error_handling: Handles malformed columns explicitly by logging the corrupted row id or text locally to standard output and mathematically skipping the row to continue executing the rest of the batch unhindered.
