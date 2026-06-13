# Method

This publish tree exposes the public-safe method surface only.

## Columbia workflow

1. Start from the OR/WA/ID corridor source layer.
2. Geocode organizations and calculate distance to the corridor centerline.
3. Assign corridor bands and regions.
4. Apply NTEE sector mapping and corridor scoring.
5. Export a public-safe CSV that excludes street address, named contacts, and private review surfaces.

## Notes

- `distance_to_centerline` is published in miles.
- `ntee_code` is published from the raw source NTEE field; missing or invalid raw values remain blank rather than being backfilled with derived placeholders.
- `funder_flag` is a v1 screening flag based on public source evidence now available in the local source snapshot: foundation-code markers (`2`, `3`, `4`), private-foundation filing requirement code (`1`), or `T*` NTEE classification.
- The scripts in `scripts/` are copied from the source project as method artifacts; private source assets are not redistributed here.
