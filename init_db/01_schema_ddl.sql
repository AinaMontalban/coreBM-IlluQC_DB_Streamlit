-- IlluQC Database Schema – DDL (table creation only)
-- Adapted for Multi-Platform Sequencing QC
--
-- This file is executed FIRST by docker-entrypoint-initdb.d (alphabetical order).
-- Seed / reference data lives in 02_schema_seed.sql.

-- =========================
-- Dimension Tables
-- =========================

CREATE TABLE IF NOT EXISTS sequencing_platforms (
    platform_id   TEXT PRIMARY KEY,      -- e.g. 'ILLUMINA', 'THERMOFISHER'
    platform_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS instruments (
    instrument_id TEXT PRIMARY KEY,
    instrument_name TEXT,
    instrument_model TEXT,
    instrument_type TEXT,
    platform_id TEXT,
    FOREIGN KEY (platform_id) REFERENCES sequencing_platforms(platform_id)
);

-- Sample metadata (clinical / lab context for each sample)
CREATE TABLE IF NOT EXISTS samples (
    sample_id TEXT PRIMARY KEY,
    sex TEXT,                             -- e.g. 'M', 'F', 'Unknown'
    virtual_panel TEXT                    -- target gene panel or assay name
);

-- Library dimension (capture / enrichment kits used for library preparation)
CREATE TABLE IF NOT EXISTS library (
    library_id TEXT PRIMARY KEY,          -- unique kit identifier
    library_name TEXT NOT NULL,           -- human-readable name
    library_version TEXT,                 -- kit version (e.g. '2.0', '8.0')
    library_type TEXT                     -- e.g. 'WES', 'WGS', 'Panel', 'Amplicon'
);

-- Dictionary of chemistry attribute types (long-format dimension)
CREATE TABLE IF NOT EXISTS chemistry_attribute_definitions (
    attribute_id TEXT PRIMARY KEY,        -- e.g. 'FLOWCELL_NAME', 'CHIP_TYPE'
    attribute_name TEXT NOT NULL,         -- human-readable name
    platform_id TEXT,                     -- NULL = shared across platforms
    description TEXT,
    FOREIGN KEY (platform_id) REFERENCES sequencing_platforms(platform_id)
);

-- Actual attribute values (long format: one row per run × attribute)
CREATE TABLE IF NOT EXISTS sequencing_chemistry_attributes (
    run_id TEXT NOT NULL,
    attribute_id TEXT NOT NULL,
    attribute_value TEXT,
    UNIQUE (run_id, attribute_id),
    FOREIGN KEY (attribute_id) REFERENCES chemistry_attribute_definitions(attribute_id)
);

-- Date dimension: day_id is the date (YYYY-MM-DD)
CREATE TABLE IF NOT EXISTS day (
    day_id DATE PRIMARY KEY,
    operator TEXT
);

-- =========================
-- Core Sequencing Tables
-- =========================

-- Sequencing chemistry look-up (pre-defined chemistry names)
CREATE TABLE IF NOT EXISTS sequencing_chemistry (
    sequencing_chemistry_id TEXT PRIMARY KEY,
    chemistry_name TEXT NOT NULL,
    platform_id TEXT,
    FOREIGN KEY (platform_id) REFERENCES sequencing_platforms(platform_id)
);

-- Core run-level record (platform-agnostic)
CREATE TABLE IF NOT EXISTS sequencing_run (
    run_id TEXT NOT NULL,
    run_folder TEXT NOT NULL,
    run_description TEXT,
    day_id DATE NOT NULL,
    instrument_id TEXT,
    platform_id TEXT NOT NULL,
    sequencing_chemistry_id TEXT,

    -- Common fields (optional; fill when available)
    num_cycles INTEGER,
    num_samples INTEGER,

    PRIMARY KEY (run_id, day_id),
    FOREIGN KEY (day_id) REFERENCES day(day_id),
    FOREIGN KEY (instrument_id) REFERENCES instruments(instrument_id),
    FOREIGN KEY (platform_id) REFERENCES sequencing_platforms(platform_id),
    FOREIGN KEY (sequencing_chemistry_id) REFERENCES sequencing_chemistry(sequencing_chemistry_id)
);

-- =========================
-- QC Metric Tables
-- =========================

-- Metric dictionary (defines what a metric is, its unit and type)
CREATE TABLE IF NOT EXISTS qc_metric_definitions (
    metric_id TEXT PRIMARY KEY,          -- e.g. 'CLUSTER_DENSITY', 'Q20_BASES_PCT'
    metric_name TEXT NOT NULL,
    display_label TEXT,                  -- human-friendly label shown in the UI (e.g. 'Cluster Density (K/mm²)')
    workflow_step TEXT,                  -- NGS workflow step: 'sequencing', 'demultiplexing', 'alignment', 'variant_calling', etc.
    scope TEXT NOT NULL DEFAULT 'run',   -- 'run' or 'sample'
    unit TEXT,
    value_type TEXT NOT NULL DEFAULT 'number', -- 'number' or 'text'
    platform_id TEXT,                    -- NULL = shared across platforms
    description TEXT,
    FOREIGN KEY (platform_id) REFERENCES sequencing_platforms(platform_id)
);

-- Actual metric values (long format; avoids schema changes per platform)
CREATE TABLE IF NOT EXISTS sequencing_qc_metrics (
    run_id TEXT NOT NULL,
    day_id DATE NOT NULL,
    metric_id TEXT NOT NULL,
    value_number DOUBLE PRECISION,
    PRIMARY KEY (run_id, day_id, metric_id),
    FOREIGN KEY (run_id, day_id) REFERENCES sequencing_run(run_id, day_id),
    FOREIGN KEY (metric_id) REFERENCES qc_metric_definitions(metric_id)
);

-- Per-sample QC metrics (long format; one row per sample × read × metric)
CREATE TABLE IF NOT EXISTS sample_qc_metrics (
    sample_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    read TEXT NOT NULL,                  -- 'R1', 'R2', or '' if not applicable
    metric_id TEXT NOT NULL,
    value_number DOUBLE PRECISION,
    PRIMARY KEY (sample_id, run_id, read, metric_id),
    FOREIGN KEY (sample_id) REFERENCES samples(sample_id),
    FOREIGN KEY (metric_id) REFERENCES qc_metric_definitions(metric_id)
);

-- Junction table linking samples to library kits per run
CREATE TABLE IF NOT EXISTS sample_library (
    sample_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    library_id TEXT NOT NULL,
    PRIMARY KEY (sample_id, run_id),
    FOREIGN KEY (sample_id) REFERENCES samples(sample_id),
    FOREIGN KEY (library_id) REFERENCES library(library_id)
);

-- =========================
-- Metadata
-- =========================

CREATE TABLE IF NOT EXISTS schema_metadata (
    key TEXT PRIMARY KEY,
    value TEXT
);
