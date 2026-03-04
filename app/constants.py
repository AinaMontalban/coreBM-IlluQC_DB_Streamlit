"""Display labels and rename maps shared across Streamlit pages."""

# ---------------------------------------------------------------------------
# Column rename: DB column name → user-friendly label
# ---------------------------------------------------------------------------

COLUMN_LABELS = {
    "run_id": "Run ID",
    "run_description": "Run Description",
    "run_folder": "Run Folder",
    "day_id": "Day ID",
    "instrument_id": "Instrument ID",
    "instrument_model": "Instrument Model",
    "instrument_name": "Instrument Name",
    "platform_id": "Platform",
    "sequencing_chemistry_id": "Sequencing Chemistry ID",
    "flowcell_part_number": "Flowcell Part Number",
    "flowcell_name": "Flowcell Name",
    "reagent_kit_part_number": "Reagent Kit Part Number",
    "reagent_kit_name": "Reagent Kit Name",
    "num_samples": "Number of Samples",
    "num_cycles": "Number of Cycles",
}

# ---------------------------------------------------------------------------
# Metric label map: metric_name from DB → display label (per platform)
# ---------------------------------------------------------------------------

METRIC_LABEL_MAP_BY_PLATFORM = {
    "ILLUMINA": {
        "cluster_density": "Cluster Density (K/mm²)",
        "cluster_pf": "% PF Clusters",
        "q30": "% Q30 Reads",
        "yield": "Yield (Gb)",
        "percent_phix_aligned": "% PhiX Aligned",
    },
    "THERMOFISHER": {
        "total_reads": "Total Reads",
        "mean_read_length": "Mean Read Length (bp)",
        "q20_bases_pct": "% Bases ≥ Q20",
        "loading_pct": "Loading %",
        "throughput_mb": "Throughput (Mb)",
    },
}

# Flat combined map (for convenience when platform is unknown or for pivot columns)
METRIC_LABEL_MAP = {
    k: v
    for platform_map in METRIC_LABEL_MAP_BY_PLATFORM.values()
    for k, v in platform_map.items()
}

# ---------------------------------------------------------------------------
# Sample bioinfo analyses column rename
# ---------------------------------------------------------------------------

SAMPLES_BIOINFO_LABELS = {
    "sample_id": "Sample ID",
    "sex": "Reported Sex",
    "virtual_panel": "Virtual Panel",
    "mean_coverage": "Mean Coverage",
    "cov_20x": "Coverage 20x (%)",
    "cov_38x": "Coverage 38x (%)",
    "percent_on_target_reads": "Percent On Target Reads (%)",
    "coverage_uniformity": "Coverage Uniformity (%)",
}
