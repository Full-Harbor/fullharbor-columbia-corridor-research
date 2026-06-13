# Columbia Corridor Research

Place-based social infrastructure research scan of nonprofit organizations near the Columbia River and Lower Snake corridor.

## Status

- Release: v1.0
- Boundary: corridor universe + NTEE classification + public-source funder screen from primary IRS EO BMF
- Deferred to v1.1: filing-derived financials beyond revenue/assets and evidence-tiered funder classes

## Method spine

Centerline -> distance bands -> IRS EO BMF org universe -> ZIP geocode -> NTEE classification -> score/flag -> public corridor scan.

## Source purity

- Organization universe: primary IRS EO BMF bulk data.
- Filing-derived fields (e.g. `total_revenue`, `total_assets`): IRS TEOS index + GivingTuesday S3 lineage.
- No ProPublica inputs.
- v1.1 work is tracked in `ROADMAP.md`; release notes are in `CHANGELOG.md`.

## Included

- `data/columbia_corridor_public.csv`
- `scripts/` method artifacts used to build the public scan

## Limitations

- Blank `ntee_code` values are documented source absence, not a category.
- IRS EO BMF does not carry `total_expenses`; v1 therefore publishes `total_revenue` and `total_assets` only when present in source lineage.
- Electronic filing became mandatory for tax years ending July 2020+; older filing-derived coverage is thinner and belongs to v1.1 enrichment work.
- 990-N filers carry no financial statements.

## License and Citation

- Public-source here means built from public filings and documents, not that every file is public-domain.
- Code in `scripts/`: MIT (`LICENSE`)
- Data and documentation: CC0 1.0 (`LICENSE-DATA`)
- Citation metadata: `CITATION.cff`

See `METHOD.md`, `DATA_DICTIONARY.md`, `LIMITATIONS.md`, `CHANGELOG.md`, and `ROADMAP.md` for details.
