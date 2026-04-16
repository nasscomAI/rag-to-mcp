# Skills

## `classify_complaint`
- **Input:** one complaint row (dict with description, location fields)
- **Output:** dict with category, priority, reason, flag
- **Error handling:** vague/short descriptions → Other + NEEDS_REVIEW

## `batch_classify`
- **Input:** path to test CSV file
- **Output:** path to results CSV file
- **Error handling:** malformed rows logged and skipped, processing continues
