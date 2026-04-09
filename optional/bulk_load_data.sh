#!/usr/bin/env bash
# Bulk-load all parsed sequencing CSVs into the PostgreSQL database.
# Usage: cd coreBM-IlluQC_DB_Streamlit && bash optional/bulk_load_data.sh

set -euo pipefail

local_folder="/Users/amontalban/HCB-Work/Doctorat/P005-multiplatform/"
common_folder="/real_data/RUNS_4"
samples_folder="/real_data/samples_metrics"

db_folder="$local_folder$common_folder"

for run_file in "$db_folder"/*-sequencing-info.csv; do
    run=$(basename "$run_file")
    run_id=$(echo "$run" | cut -d'-' -f1)
    echo "========== Uploading data for run: $run_id =========="

    # 1. sequencing_run (run info)
    docker-compose run --rm \
        -v "$(pwd)/../real_data:/app/real_data:ro" \
        loader python /app/upload_CSV.py \
        --host db --port 5432 --db illuqcdb --user postgres --password postgres \
        --table sequencing_run --csv "/app${common_folder}/${run_id}-sequencing-info.csv" \
        --fields /app/init_db/required_fields.json

    # 2. sequencing_qc_metrics (long-format metrics)
    docker-compose run --rm \
        -v "$(pwd)/../real_data:/app/real_data:ro" \
        loader python /app/upload_CSV.py \
        --host db --port 5432 --db illuqcdb --user postgres --password postgres \
        --table sequencing_qc_metrics --csv "/app${common_folder}/${run_id}-sequencing-metrics.csv" \
        --fields /app/init_db/required_fields.json

    # 3. sample_qc_metrics (long-format per-sample metrics, if CSV exists)
    sample_csv="/app${samples_folder}/${run_id}-samples-qc-metrics.csv"
    local_sample_csv="$local_folder${samples_folder}/${run_id}-samples-qc-metrics.csv"
    if [ -f "$local_sample_csv" ]; then
        docker-compose run --rm \
            -v "$(pwd)/../real_data:/app/real_data:ro" \
            loader python /app/upload_CSV.py \
            --host db --port 5432 --db illuqcdb --user postgres --password postgres \
            --table sample_qc_metrics --csv "$sample_csv" \
            --fields /app/init_db/required_fields.json
    else
        echo "  ⚠ No sample QC metrics CSV found for $run_id — skipping."
    fi
done
