-- IlluQC Database Schema (PostgreSQL) - Adapted for Multi-Platform Sequencing QC

-- =========================
-- Dimension Tables
-- =========================

CREATE TABLE IF NOT EXISTS sequencing_platforms (
    platform_id   TEXT PRIMARY KEY,      -- e.g. 'ILLUMINA', 'THERMOFISHER'
    platform_name TEXT NOT NULL
);

-- Optional seed values
INSERT INTO sequencing_platforms(platform_id, platform_name) VALUES
('ILLUMINA', 'Illumina'),
('THERMOFISHER', 'Thermo Fisher (Ion Torrent)')
ON CONFLICT (platform_id) DO NOTHING;


CREATE TABLE IF NOT EXISTS instruments (
    instrument_id TEXT PRIMARY KEY,
    instrument_name TEXT,
    instrument_model TEXT,
    instrument_type TEXT,
    platform_id TEXT,                    -- NEW
    FOREIGN KEY (platform_id) REFERENCES sequencing_platforms(platform_id)
);

CREATE TABLE IF NOT EXISTS sequencing_chemistry (
    sequencing_chemistry_id TEXT PRIMARY KEY,
    flowcell_name TEXT,
    flowcell_part_number TEXT,
    reagent_kit_name TEXT,
    reagent_kit_part_number TEXT,
    instrument_model TEXT
);



CREATE TABLE IF NOT EXISTS protocols (
    protocol_id TEXT PRIMARY KEY,
    protocol_name TEXT,
    protocol_type TEXT,
    description TEXT
);

-- Date dimension: day_id is the date (YYYY-MM-DD)
CREATE TABLE IF NOT EXISTS day (
    day_id DATE PRIMARY KEY,
    operator TEXT
);

-- Populate day table with dates from 2020-01-01 to 2050-12-31
INSERT INTO day (day_id)
SELECT d::date
FROM generate_series('2020-01-01'::date, '2050-12-31'::date, interval '1 day') AS t(d)
ON CONFLICT DO NOTHING;


-- -------------------------
-- Multi-platform sequencing QC (core + metrics)
-- -------------------------

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
    flowcell_part_number TEXT,
    reagent_kit_part_number TEXT,
    num_cycles INTEGER,
    num_samples INTEGER,

    PRIMARY KEY (run_id, day_id),
    FOREIGN KEY (day_id) REFERENCES day(day_id),
    FOREIGN KEY (instrument_id) REFERENCES instruments(instrument_id),
    FOREIGN KEY (platform_id) REFERENCES sequencing_platforms(platform_id),
    FOREIGN KEY (sequencing_chemistry_id) REFERENCES sequencing_chemistry(sequencing_chemistry_id)
);

-- Metric dictionary (defines what a metric is, its unit and type)
CREATE TABLE IF NOT EXISTS qc_metric_definitions (
    metric_id TEXT PRIMARY KEY,          -- e.g. 'Q30', 'ION_Q20_BASES_PCT'
    metric_name TEXT NOT NULL,
    scope TEXT NOT NULL DEFAULT 'run',   -- 'run' (this table), could extend to 'sample' later
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

-- Example Thermo Fisher / Ion Torrent metric definitions (edit to match your export fields)
INSERT INTO qc_metric_definitions(metric_id, metric_name, platform_id, unit, value_type, description) VALUES
('ION_READS_TOTAL',        'Total reads',              'THERMOFISHER', 'reads', 'number', 'Total reads produced'),
('ION_READ_LENGTH_MEAN',   'Mean read length',         'THERMOFISHER', 'bp',    'number', 'Average read length'),
('ION_Q20_BASES_PCT',      '% bases >= Q20',           'THERMOFISHER', '%',     'number', 'Percent bases with Q>=20'),
('ION_LOADING_PCT',        'Loading %',                'THERMOFISHER', '%',     'number', 'Chip loading percentage'),
('ION_THROUGHPUT_MB',      'Throughput',               'THERMOFISHER', 'Mb',    'number', 'Total bases in Mb')
ON CONFLICT (metric_id) DO NOTHING;

-- Example Illumina metric definitions (maps to your current columns)
INSERT INTO qc_metric_definitions(metric_id, metric_name, platform_id, unit, value_type, description) VALUES
('CLUSTER_DENSITY',        'Cluster density',          'ILLUMINA',     'k/mm2',      'number', 'Cluster density'),
('CLUSTER_PF_PCT',         '% Clusters Passing Filter','ILLUMINA',     '%',     'number', 'Percent clusters passing filter'),
('Q30_PCT',                '% Bases >= Q30',           'ILLUMINA',     '%',     'number', 'Percent bases with Q>=30'),
('YIELD',                  'Yield',                    'ILLUMINA',     'GB',      'number', 'Total yield'),
('PHIX_ALIGNED_PCT',       '% PhiX aligned',           'ILLUMINA',     '%',     'number', 'Percent PhiX aligned')
ON CONFLICT (metric_id) DO NOTHING;



-- =========================
-- Metadata
-- =========================

CREATE TABLE IF NOT EXISTS schema_metadata (
    key TEXT PRIMARY KEY,
    value TEXT
);

INSERT INTO schema_metadata (key, value) VALUES
('schema_name', 'IlluQC Database'),
('schema_version', '1.1-multiplatform')
ON CONFLICT (key) DO NOTHING;
