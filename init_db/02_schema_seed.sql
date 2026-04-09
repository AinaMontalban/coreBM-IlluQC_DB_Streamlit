-- IlluQC Database Schema – Seed / Reference Data
-- Adapted for Multi-Platform Sequencing QC
--
-- This file is executed AFTER 01_schema_ddl.sql (alphabetical order).
-- To add a new metric, append an INSERT to the appropriate section below.
-- The Streamlit app reads display_label automatically — no code changes needed.

-- =========================
-- Sequencing Platforms
-- =========================

INSERT INTO sequencing_platforms(platform_id, platform_name) VALUES
('ILLUMINA', 'Illumina'),
('THERMOFISHER', 'Thermo Fisher (Ion Torrent)')
ON CONFLICT (platform_id) DO NOTHING;

-- =========================
-- Chemistry Attribute Definitions
-- =========================

-- Illumina
INSERT INTO chemistry_attribute_definitions(attribute_id, attribute_name, platform_id, description) VALUES
('FLOWCELL_NAME',           'Flowcell name',            'ILLUMINA',     'Illumina flowcell / dry-cartridge name'),
('FLOWCELL_PART_NUMBER',    'Flowcell part number',     'ILLUMINA',     'Illumina flowcell part number'),
('REAGENT_KIT_NAME',        'Reagent kit name',         'ILLUMINA',     'Illumina reagent / wet-cartridge name'),
('REAGENT_KIT_PART_NUMBER', 'Reagent kit part number',  'ILLUMINA',     'Illumina reagent kit part number')
ON CONFLICT (attribute_id) DO NOTHING;

-- Thermo Fisher / Ion Torrent
INSERT INTO chemistry_attribute_definitions(attribute_id, attribute_name, platform_id, description) VALUES
('CHIP_TYPE',               'Chip type',                'THERMOFISHER', 'Ion Torrent chip type (e.g. 530, 520)'),
('CHIP_BARCODE',            'Chip barcode',             'THERMOFISHER', 'Ion Torrent chip barcode'),
('CHEF_REAGENTS_PART',      'Chef reagents part',       'THERMOFISHER', 'Ion Chef reagents part number'),
('TEMPLATING_KIT_NAME',     'Templating kit name',      'THERMOFISHER', 'Ion Chef templating kit'),
('LIBRARY_KIT_NAME',        'Library kit name',         'THERMOFISHER', 'Library preparation kit'),
('SEQUENCING_KIT_NAME',     'Sequencing kit name',      'THERMOFISHER', 'Ion Torrent sequencing kit')
ON CONFLICT (attribute_id) DO NOTHING;

-- =========================
-- Day Dimension (pre-populated date range)
-- =========================

INSERT INTO day (day_id)
SELECT d::date
FROM generate_series('2020-01-01'::date, '2050-12-31'::date, interval '1 day') AS t(d)
ON CONFLICT DO NOTHING;

-- =========================
-- QC Metric Definitions
-- =========================
-- To add a new metric, just append an INSERT here.
-- The app picks up display_label automatically from the database.

-- Illumina run-level metrics
INSERT INTO qc_metric_definitions(metric_id, metric_name, display_label, workflow_step, platform_id, unit, value_type, description) VALUES
('CLUSTER_DENSITY',        'cluster_density',     'Cluster Density (K/mm²)',  'sequencing', 'ILLUMINA', 'k/mm2', 'number', 'Cluster density'),
('CLUSTER_PF_PCT',         'cluster_pf',          '% PF Clusters',           'sequencing', 'ILLUMINA', '%',     'number', 'Percent clusters passing filter'),
('Q30_PCT',                'q30',                 '% Q30 Reads',             'sequencing', 'ILLUMINA', '%',     'number', 'Percent bases with Q>=30'),
('YIELD',                  'yield',               'Yield (Gb)',              'sequencing', 'ILLUMINA', 'GB',    'number', 'Total yield'),
('PHIX_ALIGNED_PCT',       'percent_phix_aligned','% PhiX Aligned',          'sequencing', 'ILLUMINA', '%',     'number', 'Percent PhiX aligned')
ON CONFLICT (metric_id) DO NOTHING;

-- Thermo Fisher / Ion Torrent run-level metrics
INSERT INTO qc_metric_definitions(metric_id, metric_name, display_label, workflow_step, platform_id, unit, value_type, description) VALUES
('READS_TOTAL',        'total_reads',        'Total Reads',            'sequencing', 'THERMOFISHER', 'reads', 'number', 'Total reads produced'),
('READ_LENGTH_MEAN',   'mean_read_length',   'Mean Read Length (bp)',   'sequencing', 'THERMOFISHER', 'bp',    'number', 'Average read length'),
('Q20_BASES_PCT',      'q20_bases_pct',      '% Bases ≥ Q20',         'sequencing', 'THERMOFISHER', '%',     'number', 'Percent bases with Q>=20'),
('LOADING_PCT',        'loading_pct',        'Loading %',              'sequencing', 'THERMOFISHER', '%',     'number', 'Chip loading percentage'),
('ADDRESS_AVAILABLE',  'address_available',  'Address Available',      'sequencing', 'THERMOFISHER', 'Wells', 'number', 'Well Addresses available')
ON CONFLICT (metric_id) DO NOTHING;

-- FastQC per-sample metrics (scope = sample, platform-agnostic)
INSERT INTO qc_metric_definitions(metric_id, metric_name, display_label, workflow_step, scope, unit, value_type, description) VALUES
('FASTQC_TOTAL_SEQUENCES',       'Total sequences',       'Total Sequences',             'demultiplexing', 'sample', 'reads',  'number', 'Total number of sequences in FASTQ'),
('FASTQC_PERCENT_FAILS',         'Percent fails',         'Percent Fails (%)',           'demultiplexing', 'sample', '%',      'number', 'Percentage of sequences failing QC checks'),
('FASTQC_GC_PCT',                'Percent GC',            'GC Content (%)',              'demultiplexing', 'sample', '%',      'number', 'GC content percentage'),
('FASTQC_PERCENT_DUPLICATES',    'Percent duplicates',    'Duplicates (%)',              'demultiplexing', 'sample', '%',      'number', 'Percentage of duplicate reads'),
('FASTQC_AVG_SEQUENCE_LENGTH',   'Avg sequence length',   'Avg Sequence Length (bp)',    'demultiplexing', 'sample', 'bp',     'number', 'Average sequence length')
ON CONFLICT (metric_id) DO NOTHING;

-- =========================
-- Schema Metadata
-- =========================

INSERT INTO schema_metadata (key, value) VALUES
('schema_name', 'IlluQC Database'),
('schema_version', '1.5-multiplatform-longformat-library')
ON CONFLICT (key) DO NOTHING;
