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
    "chemistry_name": "Chemistry Name",
    "num_samples": "Number of Samples",
    "num_cycles": "Number of Cycles",
}

# ---------------------------------------------------------------------------
# NOTE: Metric label maps (METRIC_LABEL_MAP, SAMPLE_METRIC_LABEL_MAP) are
# now driven by the ``display_label`` column in the ``qc_metric_definitions``
# database table.  Use ``queries.get_metric_label_maps(engine)`` to obtain
# them at runtime.  Adding a new metric only requires an INSERT into the DB;
# no code changes are needed here.
# ---------------------------------------------------------------------------
