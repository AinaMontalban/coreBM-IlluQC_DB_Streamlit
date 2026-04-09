#!/usr/bin/env python3
"""Generate realistic test data for the IlluQC database.

Creates 3 sequencing runs (2 Illumina, 1 ThermoFisher) with 24 samples each.
All CSVs follow the exact format expected by upload_CSV.py.

Usage:
    python generate_test_data.py          # writes to current directory
    python generate_test_data.py --outdir /path/to/output
"""

import argparse
import csv
import os
import random

random.seed(42)  # reproducible data

# ============================================================================
# Configuration
# ============================================================================

RUNS = [
    {
        "run_id": "TEST_RUN_001",
        "run_folder": "260301_M00289_0900_000000000-TESTAA",
        "run_description": "HLA",
        "day_id": "2026-03-01",
        "instrument_id": "M00289",
        "platform_id": "ILLUMINA",
        "sequencing_chemistry_id": "15033572_15035217",
        "num_cycles": 300,
    },
    {
        "run_id": "TEST_RUN_002",
        "run_folder": "260310_M06751_0200_000000000-TESTBB",
        "run_description": "HLA",
        "day_id": "2026-03-10",
        "instrument_id": "M06751",
        "platform_id": "ILLUMINA",
        "sequencing_chemistry_id": "15033572_15035218",
        "num_cycles": 150,
    },
    {
        "run_id": "TEST_RUN_003",
        "run_folder": "260320_S5_0050_TEST",
        "run_description": "AMPLISEQ",
        "day_id": "2026-03-20",
        "instrument_id": "GSS5PL-0146",
        "platform_id": "THERMOFISHER",
        "sequencing_chemistry_id": "530_500",
        "num_cycles": 300,
    },
    {
        # Re-run: reuses 12 samples from TEST_RUN_001 + 12 new samples
        "run_id": "TEST_RUN_004",
        "run_folder": "260325_LH00565_0901_000000000-TESTCC",
        "run_description": "EXOME",
        "day_id": "2026-03-25",
        "instrument_id": "LH00565",
        "platform_id": "ILLUMINA",
        "sequencing_chemistry_id": "20066617_20083896",
        "num_cycles": 300,
        "reuse_count": 12,
    },
        {
        # Re-run: reuses 12 samples from TEST_RUN_001 + 12 new samples
        "run_id": "TEST_RUN_005",
        "run_folder": "260325_LH00565_0901_000000000-TESTCC",
        "run_description": "EXOME",
        "day_id": "2026-03-27",
        "instrument_id": "LH00565",
        "platform_id": "ILLUMINA",
        "sequencing_chemistry_id": "20066617_20083896",
        "num_cycles": 300,
        "reuse_from": "TEST_RUN_004",   # reuse first 12 samples from this run
        "reuse_count": 12,
    },
]

NUM_SAMPLES_PER_RUN = 24

LIBRARIES = [
    {"library_id": "TEST_LIB_WES_TWIST",  "library_name": "Twist Exome 2.0 + CBM Spike-in", "library_version": "2.0", "library_type": "WES"},
    {"library_id": "TEST_LIB_WES_AGIL",   "library_name": "Agilent SureSelect XT HS2 v8",   "library_version": "8.0", "library_type": "WES"},
    {"library_id": "TEST_LIB_PANEL_AMP",   "library_name": "AmpliSeq HiFi Panel",            "library_version": "1.0", "library_type": "Panel"}
]

# Metric ranges per platform
ILLUMINA_METRICS = {
    "CLUSTER_DENSITY":  (600, 1200),
    "CLUSTER_PF_PCT":   (80, 98),
    "Q30_PCT":          (85, 98),
    "YIELD":            (0.5, 15.0),
    "PHIX_ALIGNED_PCT": (0.5, 3.0),
}

THERMOFISHER_METRICS = {
    "READS_TOTAL":      (3_000_000, 20_000_000),
    "READ_LENGTH_MEAN": (100, 250),
    "Q20_BASES_PCT":    (80, 97),
    "LOADING_PCT":      (60, 98),
    "ADDRESS_AVAILABLE": (10_000_000, 40_000_000),
}

SAMPLE_METRICS = {
    "FASTQC_TOTAL_SEQUENCES":     (10_000, 500_000),
    "FASTQC_PERCENT_FAILS":       (0, 50),
    "FASTQC_GC_PCT":              (35, 60),
    "FASTQC_PERCENT_DUPLICATES":  (5, 95),
    "FASTQC_AVG_SEQUENCE_LENGTH": (100, 300),
}

# Map each run to a library kit (Illumina → WES kits, ThermoFisher → Panel kit)
RUN_LIBRARY_MAP = {
    "TEST_RUN_001": "TEST_LIB_WES_TWIST",
    "TEST_RUN_002": "TEST_LIB_WES_AGIL",
    "TEST_RUN_003": "TEST_LIB_PANEL_AMP",
    "TEST_RUN_004": "TEST_LIB_WES_TWIST",   # re-run uses same library as RUN_001
    "TEST_RUN_005": "TEST_LIB_WES_TWIST",   # re-run uses same library as RUN_004
}

VIRTUAL_PANELS = ["Panel-Cardio", "Panel-Neuro", "Panel-Rare-Disease"]
SEX_OPTIONS = ["M", "F"]


# ============================================================================
# Helpers
# ============================================================================

def write_csv(filepath, fieldnames, rows):
    """Write a list of dicts to a CSV file."""
    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  ✓ {filepath}  ({len(rows)} rows)")


def rand_val(lo, hi, decimals=4):
    """Random float between lo and hi, rounded."""
    return round(random.uniform(lo, hi), decimals)


def generate_sample_ids(run_index, n=NUM_SAMPLES_PER_RUN):
    """Generate n unique sample IDs for a given run.

    Format: 26XXXXXXX — starts with 2-digit year (26) followed by 7 random digits.
    """
    ids = set()
    while len(ids) < n:
        digits = "".join([str(random.randint(0, 9)) for _ in range(7)])
        ids.add(f"26{digits}")
    return sorted(ids)


# ============================================================================
# Main
# ============================================================================

def main():
    ap = argparse.ArgumentParser(description="Generate test data for IlluQC DB.")
    ap.add_argument("--outdir", default=os.path.dirname(os.path.abspath(__file__)),
                    help="Output directory (default: same as script)")
    args = ap.parse_args()
    outdir = args.outdir

    print(f"Generating test data in: {outdir}\n")



    # ------------------------------------------------------------------
    # 3. Libraries
    # ------------------------------------------------------------------
    write_csv(
        os.path.join(outdir, "library.csv"),
        ["library_id", "library_name", "library_version", "library_type"],
        LIBRARIES,
    )

    # ------------------------------------------------------------------
    # 4. Samples metadata (all samples across all runs)
    # ------------------------------------------------------------------
    all_samples = []
    all_sample_ids_set = set()          # track already-created sample metadata
    run_sample_map = {}                 # run_id → [sample_ids]

    for idx, run in enumerate(RUNS):
        reuse_from = run.get("reuse_from")
        reuse_count = run.get("reuse_count", 0)

        if reuse_from and reuse_from in run_sample_map:
            # Reuse the first N samples from another run
            reused = run_sample_map[reuse_from][:reuse_count]
            new_count = NUM_SAMPLES_PER_RUN - reuse_count
            # Generate new unique IDs that don't collide with existing ones
            new_ids = []
            while len(new_ids) < new_count:
                candidate = f"26{''.join([str(random.randint(0, 9)) for _ in range(7)])}"
                if candidate not in all_sample_ids_set and candidate not in new_ids:
                    new_ids.append(candidate)
            sample_ids = reused + sorted(new_ids)
        else:
            sample_ids = generate_sample_ids(idx + 1, NUM_SAMPLES_PER_RUN)

        run_sample_map[run["run_id"]] = sample_ids

        for sid in sample_ids:
            if sid not in all_sample_ids_set:
                all_sample_ids_set.add(sid)
                all_samples.append({
                    "sample_id": sid,
                    "sex": random.choice(SEX_OPTIONS),
                    "virtual_panel": random.choice(VIRTUAL_PANELS),
                })

    write_csv(
        os.path.join(outdir, "samples.csv"),
        ["sample_id", "sex", "virtual_panel"],
        all_samples,
    )

    # ------------------------------------------------------------------
    # 5. Sample ↔ Library mapping (one row per sample × run)
    # ------------------------------------------------------------------
    sample_library_rows = []
    for run in RUNS:
        rid = run["run_id"]
        lib_id = RUN_LIBRARY_MAP[rid]
        for sid in run_sample_map[rid]:
            sample_library_rows.append({
                "sample_id": sid,
                "run_id": rid,
                "library_id": lib_id,
            })

    write_csv(
        os.path.join(outdir, "sample_library.csv"),
        ["sample_id", "run_id", "library_id"],
        sample_library_rows,
    )

    # ------------------------------------------------------------------
    # 6. Per-run CSVs
    # ------------------------------------------------------------------
    for run in RUNS:
        rid = run["run_id"]
        platform = run["platform_id"]
        sample_ids = run_sample_map[rid]

        # --- sequencing-info ---
        info_row = {
            "run_id": rid,
            "run_folder": run["run_folder"],
            "run_description": run["run_description"],
            "day_id": run["day_id"],
            "instrument_id": run["instrument_id"],
            "platform_id": platform,
            "sequencing_chemistry_id": run["sequencing_chemistry_id"],
            "num_cycles": run["num_cycles"],
            "num_samples": NUM_SAMPLES_PER_RUN,
        }
        write_csv(
            os.path.join(outdir, f"{rid}-sequencing-info.csv"),
            ["run_id", "run_folder", "run_description", "day_id",
             "instrument_id", "platform_id", "sequencing_chemistry_id",
             "num_cycles", "num_samples"],
            [info_row],
        )

        # --- sequencing-metrics ---
        metric_defs = ILLUMINA_METRICS if platform == "ILLUMINA" else THERMOFISHER_METRICS
        metric_rows = []
        for metric_id, (lo, hi) in metric_defs.items():
            metric_rows.append({
                "run_id": rid,
                "day_id": run["day_id"],
                "metric_id": metric_id,
                "value_number": rand_val(lo, hi),
            })
        write_csv(
            os.path.join(outdir, f"{rid}-sequencing-metrics.csv"),
            ["run_id", "day_id", "metric_id", "value_number"],
            metric_rows,
        )

        # --- samples-qc-metrics ---
        sample_rows = []
        reads = ["R1", "R2"] if platform == "ILLUMINA" else ["R1"]
        for sid in sample_ids:
            for read in reads:
                for metric_id, (lo, hi) in SAMPLE_METRICS.items():
                    sample_rows.append({
                        "sample_id": sid,
                        "run_id": rid,
                        "read": read,
                        "metric_id": metric_id,
                        "value_number": rand_val(lo, hi),
                    })
        write_csv(
            os.path.join(outdir, f"{rid}-samples-qc-metrics.csv"),
            ["sample_id", "run_id", "read", "metric_id", "value_number"],
            sample_rows,
        )

    print(f"\n✅ Done — {len(RUNS)} runs × {NUM_SAMPLES_PER_RUN} samples generated.")


if __name__ == "__main__":
    main()
