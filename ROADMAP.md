# Roadmap

## v1.1 priorities

1. Add filing-derived financial enrichment (e.g. `total_expenses`, net assets, grants paid, program/admin splits). Source order, lightest first:
   (a) NCCS Efile / NODC pre-parsed relational tables, joined by EIN;
   (b) IRS SOI Annual Extract of Tax-Exempt Org Financial Data (flat files);
   (c) fallback to filing-level XML via the existing extraction engine (IRS TEOS index + GivingTuesday S3). No ProPublica.
2. Add evidence-tiered funder classification (`funder_class` / `funder_evidence` / `funder_confidence`) so flags distinguish source basis from stronger filing-backed signals (for example 990-PF grants-paid > 0).
3. Publish a compact coverage note per enrichment field: filing-year coverage, unmatched rows, and the e-file coverage caveat (electronic filing mandatory for tax years ending July 2020+; older years and 990-N filers carry less).
4. Start with bounded slices first: high-score rows, priority-sector rows, and likely funder rows before widening to the full corpus.

## Non-goals (v1 and v1.1)

- No contact-bearing or application-private data.
- No third-party API as a data backbone (primary IRS + GivingTuesday only).
- This is place-based social infrastructure research, not a CRM.
