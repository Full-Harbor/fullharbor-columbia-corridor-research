# Data Dictionary

Columns in `data/columbia_corridor_public.csv`:

- `ein`: IRS employer identification number
- `org_name`: organization legal name
- `ntee_code`: IRS NTEE code
- `ntee_sector_letter`: first letter of NTEE code
- `city`: filer city
- `state`: filer state
- `zip`: 5-digit ZIP
- `ruling_year`: 4-digit ruling year where available
- `distance_band`: corridor proximity band from the source model
- `distance_to_centerline`: distance to corridor centerline, in miles
- `priority_flag`: whether the source model tagged the organization as sector-priority aligned
- `funder_flag`: public-source screening flag based on foundation-code markers, private-foundation filing requirement code, or `T*` NTEE classification
- `score`: normalized corridor score
- `total_revenue`: most recent public revenue amount available in source lineage
- `total_assets`: most recent public total assets amount available in source lineage
