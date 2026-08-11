# Current Taxonomy And Ollama Context

This folder preserves the active taxonomy/context bundle used for the June 30,
2026 recovery and targeted Ollama labeling work.

Use these files together as one consistent version:

- `taxonomy_from_plan.csv` - current trainable category codes and descriptions.
- `excluded_categories.csv` - no-XML/accounting-only categories excluded from prediction/training.
- `product_rules.csv` - client-confirmed product-to-category rules.
- `example_line_rules.csv` - client-confirmed row-level examples.
- `farms.csv` - known farm names.
- `category_prompt_context.txt` - the exact taxonomy/rules/examples block injected into Ollama prompts.

Do not mix these codes with older taxonomy files unless the model is retrained
and the labels are remapped intentionally.
