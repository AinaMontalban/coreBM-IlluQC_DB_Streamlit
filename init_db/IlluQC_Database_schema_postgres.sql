-- IlluQC Database Schema (PostgreSQL version)

-- =========================
-- Dimension Tables
-- =========================

CREATE TABLE samples (
    sample_id TEXT PRIMARY KEY,
    sex TEXT,
    virtual_panel TEXT
);

CREATE TABLE runs (
    run_id TEXT PRIMARY KEY,
    run_description TEXT,
    run_type TEXT
);

CREATE TABLE instruments (
    instrument_id TEXT PRIMARY KEY,
    instrument_name TEXT,
    instrument_model TEXT,
    instrument_type TEXT
);

CREATE TABLE sequencing_chemistry (
    sequencing_chemistry_id TEXT PRIMARY KEY,
    flowcell_name TEXT,
    flowcell_part_number TEXT,
    reagent_kit_name TEXT,
    reagent_kit_part_number TEXT,
    instrument_model TEXT
);
    
CREATE TABLE library (
    library_id TEXT PRIMARY KEY,
    library_name TEXT,
    library_version TEXT,
    library_type TEXT
);

CREATE TABLE protocols (
    protocol_id TEXT PRIMARY KEY,
    protocol_name TEXT,
    protocol_type TEXT,
    version TEXT,
    description TEXT
);

CREATE TABLE day (
    day_id DATE PRIMARY KEY,   -- YYYY-MM-DD
    operator TEXT
);

-- Populate day table with dates from 2020-01-01 to 2050-12-31
INSERT INTO day (day_id)
SELECT d::date
FROM generate_series('2020-01-01'::date, '2050-12-31'::date, interval '1 day') AS t(d)
ON CONFLICT DO NOTHING;

-- =========================
-- Fact Tables
-- =========================

CREATE TABLE extraction_qc (
    sample_id TEXT NOT NULL,
    day_id DATE NOT NULL,
    concentration REAL,
    a260_a280_ratio REAL,
    a260_a230_ratio REAL,
    PRIMARY KEY (sample_id, day_id),
    FOREIGN KEY (sample_id) REFERENCES samples(sample_id),
    FOREIGN KEY (day_id) REFERENCES day(day_id)
);

CREATE TABLE library_qc (
    sample_id TEXT NOT NULL,
    library_id TEXT NOT NULL,
    day_id DATE NOT NULL,
    concentration REAL,
    fragment_size REAL,
    PRIMARY KEY (sample_id, library_id, day_id),
    FOREIGN KEY (sample_id) REFERENCES samples(sample_id),
    FOREIGN KEY (library_id) REFERENCES library(library_id),
    FOREIGN KEY (day_id) REFERENCES day(day_id)
);

CREATE TABLE sequencing_qc (
    run_id TEXT NOT NULL,
    run_folder TEXT NOT NULL,
    day_id DATE NOT NULL,
    instrument_id TEXT,
    sequencing_chemistry_id TEXT,
    flowcell_part_number TEXT,
    reagent_kit_part_number TEXT,
    num_cycles INTEGER,
    num_samples INTEGER,
    cluster_density REAL,
    cluster_pf REAL,
    q30 REAL,
    yield REAL,
    percent_phix_aligned REAL,
    PRIMARY KEY (run_id, day_id, instrument_id),
    FOREIGN KEY (run_id) REFERENCES runs(run_id),
    FOREIGN KEY (instrument_id) REFERENCES instruments(instrument_id),
    FOREIGN KEY (day_id) REFERENCES day(day_id),
    FOREIGN KEY (sequencing_chemistry_id) REFERENCES sequencing_chemistry(sequencing_chemistry_id)
);

CREATE TABLE sample_bioinfo_analyses_qc (
    sample_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    library_id TEXT NOT NULL,
    day_id DATE NOT NULL,
    total_reads_r1 INTEGER,
    total_duplicated_reads_r1 INTEGER,
    gc_content_r1 REAL,
    total_reads_r2 INTEGER,
    total_duplicated_reads_r2 INTEGER,
    gc_content_r2 REAL,
    total_sequences INTEGER,
    reads_mapped INTEGER,
    reads_unmapped INTEGER,
    reads_duplicated INTEGER,
    reads_mq0 INTEGER,
    average_length REAL,
    insert_size_average REAL,
    mean_coverage REAL,
    cov_20x REAL,
    cov_38x REAL,
    percent_on_target_reads REAL,
    coverage_uniformity REAL,
    PRIMARY KEY (sample_id, run_id, library_id, day_id),
    FOREIGN KEY (sample_id) REFERENCES samples(sample_id),
    FOREIGN KEY (run_id) REFERENCES runs(run_id),
    FOREIGN KEY (library_id) REFERENCES library(library_id),
    FOREIGN KEY (day_id) REFERENCES day(day_id)
);

-- =========================
-- Metadata
-- =========================

CREATE TABLE schema_metadata (
    key TEXT PRIMARY KEY,
    value TEXT
);

INSERT INTO schema_metadata (key, value) VALUES
('schema_name', 'IlluQC Database'),
('schema_version', '1.0')
ON CONFLICT (key) DO NOTHING;
