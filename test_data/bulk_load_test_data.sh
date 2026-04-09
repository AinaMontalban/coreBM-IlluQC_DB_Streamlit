#!/usr/bin/env bash
# Bulk-load test data into the PostgreSQL database.
# Usage: cd coreBM-IlluQC_DB_Streamlit && bash test_data/bulk_load_test_data.sh

set -euo pipefail

TEST_DIR="/app/test_data"

upload() {
    local table="$1"
    local csv="$2"
    echo "  → $table  ←  $(basename "$csv")"
    docker-compose run --rm \
        -v "$(pwd)/test_data:/app/test_data:ro" \
        loader python /app/upload_CSV.py \
        --host db --port 5432 --db illuqcdb --user postgres --password postgres \
        --table "$table" --csv "$csv" \
        --fields /app/init_db/required_fields.json
}

echo "=========================================="
echo " Loading dimension / reference data"
echo "=========================================="

upload instruments              "$TEST_DIR/instruments.csv"
upload sequencing_chemistry     "$TEST_DIR/sequencing_chemistry.csv"
upload library                  "$TEST_DIR/library.csv"
upload samples                  "$TEST_DIR/samples.csv"
upload sample_library           "$TEST_DIR/sample_library.csv"

echo ""
echo "=========================================="
echo " Loading per-run data"
echo "=========================================="

for info_csv in "$(pwd)"/test_data/TEST_RUN_*-sequencing-info.csv; do
    # Derive run_id from filename (e.g. TEST_RUN_001)
    base=$(basename "$info_csv")
    run_id="${base%-sequencing-info.csv}"
    echo ""
    echo "---------- $run_id ----------"

    # 1. sequencing_run
    upload sequencing_run           "$TEST_DIR/${run_id}-sequencing-info.csv"

    # 2. sequencing_qc_metrics
    upload sequencing_qc_metrics    "$TEST_DIR/${run_id}-sequencing-metrics.csv"

    # 3. sample_qc_metrics
    sample_csv="$TEST_DIR/${run_id}-samples-qc-metrics.csv"
    upload sample_qc_metrics        "$sample_csv"
done

echo ""
echo "=========================================="
echo "  Test data loaded successfully"
echo "=========================================="
