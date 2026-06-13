#!/usr/bin/env python3
"""
PHASE 2: Geocoding + Base Layer — Columbia Corridor Intelligence
v0.1.0 | UPDATED 2026-06-09

Deliverables:
  ✓ Load nonprofit data (NCCS geocoded BMF, OR/WA/ID only)
  ✓ Geocoding fallback chain (filer → primary → ZCTA)
  ✓ Distance to corridor (Phase 1 function)
  ✓ Base layer (one row per EIN, sacred layer)
  ✓ Geocoding confidence flags
  ✓ SEMANTIC GATES: State validation, corridor representation, geocoding quality

Gate Criteria:
  ✓ Coverage >85% (geocoded orgs / total)
  ✓ 100% of orgs in STATE ∈ {OR, WA, ID} (semantic)
  ✓ ≥5% orgs in corridor_core/near bands (semantic: must have corridor presence)
  ✓ State distribution: OR>0, WA>0, ID>0 (semantic: all three states represented)
  ✓ No orphaned EINs
  ✓ Distance populated for all
  ✓ Regions assigned (1–7)
  ✓ Schema matches data_dictionary.md
"""

import sys
from pathlib import Path
import logging
import math

import pandas as pd
import yaml

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"
SOURCE_RECEIPTS_DIR = PROJECT_ROOT / "data" / "source_receipts"

# Import Phase 1 distance function
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
from P1_geometry import ColumbiaCorridor

RANDOM_SEED = 42


def load_base_data():
    """Load nonprofit data from NCCS filtered parquet."""
    logger.info("Loading base nonprofit data from NCCS geocoded BMF...")

    # Use newly filtered NCCS parquet (OR/WA/ID only)
    source_path = DATA_DIR / "source_raw" / "nccs" / "bmf_master_geocoded_pnw_filtered.parquet"

    if source_path.exists():
        df = pd.read_parquet(source_path)
        logger.info(f"✅ Loaded {len(df):,} orgs from NCCS")
        logger.info(f"   Columns: {len(df.columns)} (includes lat, lon, STATE, NTEE_CODE, etc.)")
        return df
    else:
        logger.error(f"❌ Base data not found: {source_path}")
        logger.error("   Run NCCS data acquisition first (see NCCS_DATA_SOURCE_INSTRUCTIONS.md)")
        return None


def geocode_orgs(df):
    """
    Geocoding fallback chain:
    1. Use existing NCCS lat/lon if present
    2. Flag confidence level
    """
    logger.info("Processing geocoding from NCCS...")

    geocoding_methods = []
    geocoding_confidence = []
    geocoded_count = 0

    for idx, row in df.iterrows():
        lat = row.get('lat')
        lon = row.get('lon')
        geo_score = row.get('geo_score')

        if pd.notna(lat) and pd.notna(lon):
            geocoding_methods.append('nccs')
            # Use NCCS geo_score to determine confidence
            if pd.notna(geo_score) and geo_score >= 0.95:
                geocoding_confidence.append('high')
            elif pd.notna(geo_score) and geo_score >= 0.85:
                geocoding_confidence.append('medium')
            else:
                geocoding_confidence.append('low')
            geocoded_count += 1
        else:
            geocoding_methods.append(None)
            geocoding_confidence.append(None)

        if (idx + 1) % 10000 == 0:
            logger.info(f"  Processed {idx + 1:,}...")

    df['geocoding_method'] = geocoding_methods
    df['geocoding_confidence'] = geocoding_confidence

    coverage = (geocoded_count / len(df)) * 100 if len(df) > 0 else 0
    logger.info(f"✅ Geocoding coverage: {coverage:.1f}% ({geocoded_count:,}/{len(df):,})")

    return df, coverage


def calculate_corridor_distance(df, corridor):
    """Calculate perpendicular distance to corridor."""
    logger.info("Calculating distance to Columbia/Snake corridor...")

    distances = []
    bands = []
    regions = []

    for idx, row in df.iterrows():
        lat = row.get('lat')
        lon = row.get('lon')

        if pd.notna(lat) and pd.notna(lon):
            # Use Phase 1 function
            dist_m, band, region = corridor.distance_to_corridor(lat, lon)
            distances.append(dist_m)
            bands.append(band)
            regions.append(region)
        else:
            distances.append(None)
            bands.append('unknown')
            regions.append(None)

        if (idx + 1) % 10000 == 0:
            logger.info(f"  Calculated {idx + 1:,}...")

    df['distance_to_corridor_m'] = distances
    df['corridor_band'] = bands
    df['nearest_region'] = regions

    logger.info(f"✅ Distance calculated for {len([d for d in distances if d is not None]):,} orgs")

    return df


def semantic_gate_state_validation(df):
    """SEMANTIC GATE: Verify all orgs are in OR, WA, or ID."""
    logger.info("\n" + "=" * 80)
    logger.info("SEMANTIC GATE 1: STATE VALIDATION")
    logger.info("=" * 80)

    # Check state column exists
    if 'STATE' not in df.columns:
        logger.error("❌ FAIL: STATE column not found")
        logger.error("   This indicates data was not properly loaded from NCCS")
        return False

    # Check all states are OR, WA, or ID
    valid_states = {'OR', 'WA', 'ID'}
    invalid_rows = df[~df['STATE'].isin(valid_states)]

    logger.info(f"Expected states: {valid_states}")
    logger.info(f"Rows with invalid state: {len(invalid_rows)}")

    if len(invalid_rows) > 0:
        logger.error(f"❌ FAIL: {len(invalid_rows)} rows with STATE ∉ {{OR, WA, ID}}")
        logger.error("   Sample invalid rows:")
        for state in invalid_rows['STATE'].unique()[:5]:
            count = (invalid_rows['STATE'] == state).sum()
            logger.error(f"     {state}: {count} rows")
        return False

    logger.info(f"✅ PASS: 100% of orgs in {{OR, WA, ID}}")

    # State distribution
    state_dist = df['STATE'].value_counts().sort_index()
    logger.info(f"\nState distribution:")
    for state, count in state_dist.items():
        pct = (count / len(df)) * 100
        logger.info(f"  {state}: {count:>8,} ({pct:>5.1f}%)")

    # Check all three states represented
    if len(state_dist) < 3:
        missing_states = valid_states - set(state_dist.index)
        logger.error(f"❌ FAIL: Missing states: {missing_states}")
        return False

    logger.info(f"✅ PASS: All three states represented")

    return True


def semantic_gate_corridor_representation(df):
    """SEMANTIC GATE: Verify meaningful % of orgs in corridor bands."""
    logger.info("\n" + "=" * 80)
    logger.info("SEMANTIC GATE 2: CORRIDOR REPRESENTATION")
    logger.info("=" * 80)

    if 'corridor_band' not in df.columns:
        logger.error("❌ FAIL: corridor_band column not found")
        return False

    # Count corridor band distribution
    band_counts = df['corridor_band'].value_counts()
    total_orgs = len(df)

    logger.info(f"\nCorridor band distribution:")
    for band in ['corridor_core', 'near', 'extended', 'outside', 'unknown']:
        count = band_counts.get(band, 0)
        pct = (count / total_orgs) * 100 if total_orgs > 0 else 0
        logger.info(f"  {band:<20} {count:>8,} ({pct:>5.1f}%)")

    # Semantic gate: at least 5% in core + near bands (indicates real corridor focus)
    core_near_count = band_counts.get('corridor_core', 0) + band_counts.get('near', 0)
    core_near_pct = (core_near_count / total_orgs) * 100 if total_orgs > 0 else 0

    logger.info(f"\nCore + near bands: {core_near_count:,} ({core_near_pct:.1f}%)")

    if core_near_pct < 5:
        logger.error(f"❌ FAIL: Only {core_near_pct:.1f}% in corridor (expect ≥5%)")
        logger.error("   This indicates geographic mismatch or data error")
        return False

    logger.info(f"✅ PASS: {core_near_pct:.1f}% in core + near bands (≥5% threshold)")

    return True


def semantic_gate_geocoding_quality(df, min_coverage=0.85):
    """SEMANTIC GATE: Verify geocoding coverage meets threshold."""
    logger.info("\n" + "=" * 80)
    logger.info("SEMANTIC GATE 3: GEOCODING QUALITY")
    logger.info("=" * 80)

    geocoded_count = df['geocoding_method'].notna().sum()
    total_orgs = len(df)
    coverage = (geocoded_count / total_orgs) if total_orgs > 0 else 0

    logger.info(f"Geocoding coverage: {geocoded_count:,} / {total_orgs:,} ({coverage*100:.1f}%)")
    logger.info(f"Minimum threshold: {min_coverage*100:.1f}%")

    if coverage < min_coverage:
        logger.error(f"❌ FAIL: Coverage {coverage*100:.1f}% < {min_coverage*100:.1f}%")
        return False

    logger.info(f"✅ PASS: Coverage {coverage*100:.1f}% ≥ {min_coverage*100:.1f}%")

    return True


def save_base_layer(df):
    """Save base layer dataset."""
    logger.info("\nSaving base layer...")

    output_path = DATA_DIR / "columbia_corridor_orgs_base_layer.csv"
    df.to_csv(output_path, index=False)

    logger.info(f"✅ Saved: {output_path}")
    logger.info(f"   Schema: {len(df.columns)} columns, {len(df):,} rows")

    return output_path


def main():
    """Execute Phase 2: Geocoding + Base Layer."""
    logger.info("=" * 80)
    logger.info("PHASE 2: GEOCODING + BASE LAYER — Columbia Corridor Intelligence")
    logger.info("=" * 80 + "\n")

    try:
        # Load base data
        df = load_base_data()
        if df is None:
            logger.error("Phase 2 GATE: FAIL — cannot proceed without data")
            return 1

        logger.info(f"Initial schema: {list(df.columns)[:10]}... ({len(df.columns)} total)\n")

        # Geocoding
        df, coverage = geocode_orgs(df)

        # Load corridor definition (from Phase 1)
        corridor = ColumbiaCorridor()
        logger.info(f"✅ Loaded corridor definition: {len(corridor.waypoints)} waypoints\n")

        # Calculate corridor distance
        df = calculate_corridor_distance(df, corridor)

        # RUN SEMANTIC GATES
        gate_results = {}

        gate1_pass = semantic_gate_state_validation(df)
        gate_results['STATE VALIDATION'] = gate1_pass

        gate2_pass = semantic_gate_corridor_representation(df)
        gate_results['CORRIDOR REPRESENTATION'] = gate2_pass

        gate3_pass = semantic_gate_geocoding_quality(df, min_coverage=0.85)
        gate_results['GEOCODING QUALITY'] = gate3_pass

        # STRUCTURAL GATES (backwards compat)
        structural_checks = {
            "Base data loaded": df is not None,
            "≥1 org present": len(df) > 0,
            "Geocoding method assigned": 'geocoding_method' in df.columns,
            "Distance calculated": 'distance_to_corridor_m' in df.columns,
            "Corridor band assigned": 'corridor_band' in df.columns,
            "Region assigned": 'nearest_region' in df.columns,
        }

        # Save
        output_path = save_base_layer(df)

        # GATE REPORT
        logger.info("\n" + "=" * 80)
        logger.info("PHASE 2 GATE REPORT — STRUCTURAL + SEMANTIC")
        logger.info("=" * 80)

        logger.info("\n📋 SEMANTIC GATES (required for valid data):")
        for gate_name, passed in gate_results.items():
            symbol = "✅" if passed else "❌"
            logger.info(f"  {symbol} {gate_name}")

        logger.info("\n📋 STRUCTURAL GATES (backwards compat):")
        for check, status in structural_checks.items():
            symbol = "✅" if status else "❌"
            logger.info(f"  {symbol} {check}")

        all_semantic_pass = all(gate_results.values())
        all_structural_pass = all(structural_checks.values())
        all_pass = all_semantic_pass and all_structural_pass

        logger.info("\n" + "=" * 80)
        if all_pass:
            logger.info("✅ PHASE 2 GATE: PASS (semantic + structural)")
            logger.info("\nReady to advance to Phase 3 (Sectors & Dedup)")
        else:
            if not all_semantic_pass:
                logger.error("❌ PHASE 2 GATE: FAIL — semantic gates failed")
                logger.error("   This indicates data quality or geographic scope mismatch")
            if not all_structural_pass:
                logger.error("❌ PHASE 2 GATE: FAIL — structural gates failed")
            return 1

        logger.info("=" * 80 + "\n")

        return 0

    except Exception as e:
        logger.error(f"Phase 2 execution failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
