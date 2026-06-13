# Limitations

- Blank `ntee_code` values are documented source absence, not a category.
- Filing-derived fields such as `total_expenses` are not included in v1 because they are not present in the current BMF-derived public-safe source lineage.
- Electronic filing became mandatory for tax years ending July 2020+; older filing-derived coverage is thinner and belongs to v1.1 enrichment work.
- 990-N filers carry no financial statements.
- `funder_flag` is a corridor-screening heuristic, not proof of current grantmaking behavior.
- Published scoring reflects the local source snapshot as of 2026-06-13.
- No claim of endorsement, partnership, or current organizational capacity should be inferred from presence in the dataset.
