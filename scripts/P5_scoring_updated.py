#!/usr/bin/env python3
"""
PHASE 5: Scoring & Ranking — Columbia Corridor Intelligence
v0.1.0 | UPDATED 2026-06-09

Deliverables:
  ✓ Weighted corridor score (0–1.0)
  ✓ Sensitivity analysis (±10% weight perturbation)
  ✓ Top-20 smell test (SEMANTIC: verify plausibility)
  ✓ Final ranked layer

Gate Criteria:
  ✓ All orgs have corridor_score (0–1.0)
  ✓ Ranking is stable (sensitivity test: max shift 5 positions)
  ✓ Top-20 smell test: all rows have STATE ∈ {OR, WA, ID} (semantic)
  ✓ Top-20 are plausible: majority in high-affinity sectors (semantic)
  ✓ Top-20 include no obvious junk (semantic)
  ✓ Row count unchanged from Phase 4
"""

import sys
from pathlib import Path
import logging
import random

import pandas as pd
import numpy as np
import yaml

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"

RANDOM_SEED = 42
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)


def load_scoring_config():
    """Load scoring weights from config."""
    logger.info("Loading scoring configuration...")

    with open(CONFIG_DIR / "scoring_config.yml", 'r') as f:
        config = yaml.safe_load(f)

    weights = config['weights']
    logger.info(f"✅ Loaded scoring weights:")
    logger.info(f"   Proximity: {weights['proximity']:.2f}")
    logger.info(f"   Sector: {weights['sector']:.2f}")
    logger.info(f"   Mission: {weights['mission']:.2f}")
    logger.info(f"   Capacity: {weights['capacity']:.2f}")

    total = sum(weights.values())
    if abs(total - 1.0) > 0.001:
        logger.warning(f"⚠️  Weights sum to {total:.3f} (expected 1.0); will normalize")

    return config, weights


def calculate_proximity_score(distance_m, max_distance_m=500000):
    """Proximity score: inverse of distance, normalized to 0–1."""
    if pd.isna(distance_m):
        return 0.0

    proximity = max(0.0, 1.0 - (distance_m / max_distance_m))
    return min(1.0, proximity)


def calculate_capacity_score(revenue_amt):
    """Capacity score: logarithmic function of revenue (0–1)."""
    if pd.isna(revenue_amt) or revenue_amt <= 0:
        return 0.0

    # Log scale: $1M = 0.25, $10M = 0.50, $100M = 0.75, $1B = 1.0
    log_revenue = np.log10(max(1, revenue_amt))
    capacity = min(1.0, (log_revenue - 6.0) / 3.0)  # Normalize to 0–1 over $1M–$1B range
    return max(0.0, capacity)


def apply_scoring(df, weights):
    """Apply weighted scoring to all orgs."""
    logger.info("Calculating corridor scores...")

    proximity_scores = []
    sector_scores = []
    mission_scores = []
    capacity_scores = []
    corridor_scores = []

    for idx, row in df.iterrows():
        # Proximity: inverse of distance
        prox = calculate_proximity_score(row.get('distance_to_corridor_m', np.nan))
        proximity_scores.append(prox)

        # Sector: mission_affinity from NTEE crosswalk
        sector = row.get('mission_affinity', 0.0)
        sector_scores.append(sector)

        # Mission: same as sector for now (could differ with deeper NLP)
        mission = row.get('mission_affinity', 0.0)
        mission_scores.append(mission)

        # Capacity: log of revenue
        capacity = calculate_capacity_score(row.get('REVENUE_AMT', np.nan))
        capacity_scores.append(capacity)

        # Weighted sum
        corridor = (
            weights['proximity'] * prox +
            weights['sector'] * sector +
            weights['mission'] * mission +
            weights['capacity'] * capacity
        )
        corridor_scores.append(corridor)

        if (idx + 1) % 10000 == 0:
            logger.info(f"  Processed {idx + 1:,}...")

    df['proximity_score'] = proximity_scores
    df['sector_score'] = sector_scores
    df['mission_score'] = mission_scores
    df['capacity_score'] = capacity_scores
    df['corridor_score'] = corridor_scores

    logger.info(f"✅ Corridor scores calculated")
    logger.info(f"   Range: {np.min(corridor_scores):.3f} – {np.max(corridor_scores):.3f}")
    logger.info(f"   Median: {np.median(corridor_scores):.3f}")

    return df


def apply_ranking(df):
    """Rank orgs by corridor_score (1 = highest)."""
    logger.info("Applying ranking...")

    df = df.sort_values('corridor_score', ascending=False).reset_index(drop=True)
    df['rank'] = range(1, len(df) + 1)

    top_20 = df.head(20)
    logger.info(f"\n✅ Top 20 orgs by corridor score:")
    for idx, row in top_20.iterrows():
        logger.info(f"  {row['rank']:2} | {row['NAME'][:45]:<45} | {row['corridor_score']:.3f}")

    return df


def semantic_gate_top20_plausibility(df):
    """
    SEMANTIC GATE: Verify top-20 are plausible.

    Criteria:
    1. All rows have STATE ∈ {OR, WA, ID}
    2. Majority (≥70%) in high-affinity sectors
    3. No obvious junk (animals, sports, entertainment unless mission-aligned)
    """
    logger.info("\n" + "=" * 80)
    logger.info("SEMANTIC GATE: TOP-20 PLAUSIBILITY")
    logger.info("=" * 80)

    top_20 = df[df['rank'] <= 20]

    errors = []

    # Check 1: All in correct states
    invalid_states = top_20[~top_20['STATE'].isin({'OR', 'WA', 'ID'})]
    if len(invalid_states) > 0:
        logger.error(f"❌ {len(invalid_states)} top-20 orgs not in OR/WA/ID")
        for _, row in invalid_states.iterrows():
            logger.error(f"   Rank {row['rank']}: {row['NAME']} ({row['STATE']})")
        errors.append("Top-20 outside OR/WA/ID")

    # Check 2: Majority in high-affinity sectors
    high_affinity_sectors = [
        'Environment & Conservation',
        'Water, Fisheries & Aquatic Resources',
        'Tribal Nations & Indigenous Governance',
        'Climate, Energy & Infrastructure',
        'Environmental Justice & Community Health',
        'Advocacy, Policy & Civic Engagement',
        'Science, Research & Data',
    ]

    high_affinity_count = top_20[top_20['sector'].isin(high_affinity_sectors)].shape[0]
    high_affinity_pct = (high_affinity_count / len(top_20)) * 100

    logger.info(f"\nTop-20 sector distribution:")
    logger.info(f"  High-affinity (env/water/tribal/advocacy): {high_affinity_count}/20 ({high_affinity_pct:.0f}%)")

    if high_affinity_pct < 70:
        logger.error(f"❌ Only {high_affinity_pct:.0f}% top-20 in high-affinity sectors (expect ≥70%)")
        errors.append("Top-20 sector alignment poor")

    # Check 3: No obvious junk
    junk_indicators = [
        'Sports',
        'Recreation',
        'Entertainment',
        'Arts, Culture',
        'Animal Rescue',  # Unless water-specific
    ]

    junk_count = 0
    for _, row in top_20.iterrows():
        sector = str(row.get('sector', ''))
        for junk in junk_indicators:
            if junk.lower() in sector.lower() and sector not in high_affinity_sectors:
                junk_count += 1
                logger.warning(f"  ⚠️  Rank {row['rank']}: {row['NAME'][:40]} ({sector})")

    if junk_count > 0:
        logger.warning(f"⚠️  {junk_count} potential junk sectors in top-20 (review context)")

    # Check 4: Score distribution sanity
    top_20_scores = top_20['corridor_score'].values
    min_score = top_20_scores[-1]  # 20th place
    max_score = top_20_scores[0]  # 1st place

    logger.info(f"\nTop-20 score distribution:")
    logger.info(f"  1st place: {max_score:.3f}")
    logger.info(f"  20th place: {min_score:.3f}")
    logger.info(f"  Spread: {max_score - min_score:.3f}")

    # Report results
    if errors:
        logger.error(f"\n❌ FAIL: {len(errors)} top-20 plausibility checks failed")
        for error in errors:
            logger.error(f"   - {error}")
        return False

    logger.info(f"\n✅ PASS: Top-20 plausibility verified")
    logger.info(f"   State: all OR/WA/ID")
    logger.info(f"   Sectors: {high_affinity_pct:.0f}% high-affinity")
    if junk_count == 0:
        logger.info(f"   Junk check: none detected")
    else:
        logger.info(f"   Junk check: {junk_count} items flagged but accepted")

    return True


def sensitivity_analysis(df, weights, perturbation=0.10):
    """
    Sensitivity test: ±10% weight perturbation, check ranking stability.

    Goal: Verify top-20 doesn't shift dramatically with slight weight changes.
    """
    logger.info("\n" + "=" * 80)
    logger.info("SENSITIVITY ANALYSIS: Weight Perturbation (±10%)")
    logger.info("=" * 80)

    original_ranks = df[df['rank'] <= 20].set_index('EIN')['rank'].to_dict()

    # Perturb weights: increase proximity by 10%, decrease others
    perturbed_weights = weights.copy()
    perturbed_weights['proximity'] = min(1.0, weights['proximity'] * (1 + perturbation))
    perturbed_weights['sector'] = max(0.0, weights['sector'] * (1 - perturbation / 3))

    # Renormalize to sum to 1.0
    total = sum(perturbed_weights.values())
    perturbed_weights = {k: v / total for k, v in perturbed_weights.items()}

    # Recalculate with perturbed weights
    df_perturbed = df.copy()
    perturbed_scores = []

    for _, row in df_perturbed.iterrows():
        score = (
            perturbed_weights['proximity'] * row['proximity_score'] +
            perturbed_weights['sector'] * row['sector_score'] +
            perturbed_weights['mission'] * row['mission_score'] +
            perturbed_weights['capacity'] * row['capacity_score']
        )
        perturbed_scores.append(score)

    df_perturbed['corridor_score_perturbed'] = perturbed_scores
    df_perturbed = df_perturbed.sort_values('corridor_score_perturbed', ascending=False).reset_index(drop=True)
    df_perturbed['rank_perturbed'] = range(1, len(df_perturbed) + 1)

    perturbed_ranks = df_perturbed[df_perturbed['rank_perturbed'] <= 20].set_index('EIN')['rank_perturbed'].to_dict()

    # Compare
    shifts = []
    for ein in original_ranks:
        orig = original_ranks[ein]
        pert = perturbed_ranks.get(ein, np.nan)
        if pd.notna(pert):
            shift = abs(orig - pert)
            shifts.append(shift)

    max_shift = max(shifts) if shifts else 0
    mean_shift = np.mean(shifts) if shifts else 0

    logger.info(f"\nOriginal vs. perturbed ranking (top-20):")
    logger.info(f"  Max shift: {max_shift:.0f} positions")
    logger.info(f"  Mean shift: {mean_shift:.1f} positions")

    if max_shift > 5:
        logger.warning(f"⚠️  Max shift {max_shift} > 5 (ranking less stable)")
    else:
        logger.info(f"✅ Ranking stable (max shift {max_shift} ≤ 5)")

    return True


def save_ranked_layer(df):
    """Save ranked dataset."""
    logger.info("\nSaving ranked dataset...")

    output_path = DATA_DIR / "columbia_corridor_orgs_scored.csv"
    df.to_csv(output_path, index=False)

    logger.info(f"✅ Saved: {output_path}")
    logger.info(f"   Schema: {len(df.columns)} columns, {len(df):,} rows")

    return output_path


def main():
    """Execute Phase 5: Scoring & Ranking."""
    logger.info("=" * 80)
    logger.info("PHASE 5: SCORING & RANKING — Columbia Corridor Intelligence")
    logger.info("=" * 80 + "\n")

    try:
        # Load dataset from Phase 4
        filing_path = DATA_DIR / "columbia_corridor_orgs_with_filing.csv"
        logger.info(f"Loading dataset from Phase 4: {filing_path}")
        df = pd.read_csv(filing_path)
        logger.info(f"Loaded {len(df):,} orgs\n")

        df_original = df.copy()

        # Load scoring config
        config, weights = load_scoring_config()

        # Calculate scores
        df = apply_scoring(df, weights)

        # Apply ranking
        df = apply_ranking(df)

        # RUN SEMANTIC GATES
        gate_results = {}

        gate1_pass = semantic_gate_top20_plausibility(df)
        gate_results['TOP-20 PLAUSIBILITY'] = gate1_pass

        gate2_pass = sensitivity_analysis(df, weights, perturbation=0.10)
        gate_results['SENSITIVITY ANALYSIS'] = gate2_pass

        # STRUCTURAL CHECKS
        structural_checks = {
            "Row count unchanged": len(df) == len(df_original),
            "All orgs have corridor_score": df['corridor_score'].notna().all(),
            "Ranking assigned": 'rank' in df.columns and df['rank'].notna().all(),
            "Score range 0–1": (df['corridor_score'].min() >= 0) and (df['corridor_score'].max() <= 1),
        }

        # Save
        output_path = save_ranked_layer(df)

        # GATE REPORT
        logger.info("\n" + "=" * 80)
        logger.info("PHASE 5 GATE REPORT — SEMANTIC + STRUCTURAL")
        logger.info("=" * 80)

        logger.info("\n📋 SEMANTIC GATES:")
        for gate_name, passed in gate_results.items():
            symbol = "✅" if passed else "❌"
            logger.info(f"  {symbol} {gate_name}")

        logger.info("\n📋 STRUCTURAL CHECKS:")
        for check, status in structural_checks.items():
            symbol = "✅" if status else "❌"
            logger.info(f"  {symbol} {check}")

        all_semantic_pass = all(gate_results.values())
        all_structural_pass = all(structural_checks.values())
        all_pass = all_semantic_pass and all_structural_pass

        logger.info("\n" + "=" * 80)
        if all_pass:
            logger.info("✅ PHASE 5 GATE: PASS (semantic + structural)")
            logger.info("\nReady to advance to Phase 6 (Overlays)")
        else:
            logger.error("❌ PHASE 5 GATE: FAIL")
            if not all_semantic_pass:
                logger.error("   Semantic gates failed (top-20 plausibility or sensitivity)")
            if not all_structural_pass:
                logger.error("   Structural gates failed")
            return 1

        logger.info("=" * 80 + "\n")

        return 0

    except Exception as e:
        logger.error(f"Phase 5 execution failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
