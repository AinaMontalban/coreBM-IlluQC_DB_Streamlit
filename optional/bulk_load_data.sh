

local_folder="/Users/amontalban/HCB-Work/Doctorat/P005-multiplatform/"
common_folder="/real_data/RUNS_2"

db_folder="$local_folder$common_folder"

for run_file in "$db_folder"/*-sequencing-info.csv; do
    run=$(basename "$run_file")
    # example: R3118_run_info.csv
    # get run id from the file name
    run_id=$(echo "$run" | cut -d'-' -f1)
    echo "Uploading data for run: $run_id"

    docker-compose run --rm \
        -v "$(pwd)/../real_data:/app/real_data:ro" \
        loader python /app/upload_CSV.py \
        --host db --port 5432 --db illuqcdb --user postgres --password postgres \
        --table sequencing_run --csv "/app${common_folder}/${run_id}-sequencing-info.csv" \
        --fields /app/init_db/required_fields.json
    
    docker-compose run --rm \
        -v "$(pwd)/../real_data:/app/real_data:ro" \
        loader python /app/upload_CSV.py \
        --host db --port 5432 --db illuqcdb --user postgres --password postgres \
        --table sequencing_qc_metrics --csv "/app${common_folder}/${run_id}-sequencing-metrics.csv" \
        --fields /app/init_db/required_fields.json
done
