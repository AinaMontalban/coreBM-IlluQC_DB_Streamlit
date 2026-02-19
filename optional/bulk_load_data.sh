

db_folder="/Users/amontalban/HCB-Work/Doctorat/P004/real_data/RUNS"

for run_file in "$db_folder"/*-run_info.csv; do
    run=$(basename "$run_file")
    # example: R3118_run_info.csv
    # get run id from the file name
    run_id=$(echo "$run" | cut -d'-' -f1)
    echo "Uploading data for run: $run_id"

    docker-compose run --rm \
        -v "$(pwd)/../real_data:/app/real_data:ro" \
        loader python /app/upload_CSV.py \
        --host db --port 5432 --db illuqcdb --user postgres --password postgres \
        --table runs --csv "/app/real_data/RUNS/${run_id}-run_info.csv" \
        --fields /app/init_db/required_fields.json
done


for run_file in "$db_folder"/*-sequencing_qc.csv; do
    run=$(basename "$run_file")
    # example: R3118_run_info.csv
    # get run id from the file name
    run_id=$(echo "$run" | cut -d'-' -f1)
    echo "Uploading data for run: $run_id"

    docker-compose run --rm \
        -v "$(pwd)/../real_data:/app/real_data:ro" \
        loader python /app/upload_CSV.py \
        --host db --port 5432 --db illuqcdb --user postgres --password postgres \
        --table sequencing_qc --csv "/app/real_data/RUNS/${run_id}-sequencing_qc.csv" \
        --fields /app/init_db/required_fields.json
done



db_folder="/Users/amontalban/HCB-Work/Doctorat/P004/real_data/RUNS_HLA"

for run_file in "$db_folder"/*-run_info.csv; do
    run=$(basename "$run_file")
    # example: R3118_run_info.csv
    # get run id from the file name
    run_id=$(echo "$run" | cut -d'-' -f1)
    echo "Uploading data for run: $run_id"

    docker-compose run --rm \
        -v "$(pwd)/../real_data:/app/real_data:ro" \
        loader python /app/upload_CSV.py \
        --host db --port 5432 --db illuqcdb --user postgres --password postgres \
        --table runs --csv "/app/real_data/RUNS_HLA/${run_id}-run_info.csv" \
        --fields /app/init_db/required_fields.json
    
    docker-compose run --rm \
        -v "$(pwd)/../real_data:/app/real_data:ro" \
        loader python /app/upload_CSV.py \
        --host db --port 5432 --db illuqcdb --user postgres --password postgres \
        --table sequencing_qc --csv "/app/real_data/RUNS_HLA/${run_id}_sequencing_qc.csv" \
        --fields /app/init_db/required_fields.json
done

db_folder="/Users/amontalban/HCB-Work/Doctorat/P004/real_data/RUNS_MICROBIOME"

for run_file in "$db_folder"/*-run_info.csv; do
    run=$(basename "$run_file")
    # example: R3118_run_info.csv
    # get run id from the file name
    run_id=$(echo "$run" | cut -d'-' -f1)
    echo "Uploading data for run: $run_id"

    docker-compose run --rm \
        -v "$(pwd)/../real_data:/app/real_data:ro" \
        loader python /app/upload_CSV.py \
        --host db --port 5432 --db illuqcdb --user postgres --password postgres \
        --table runs --csv "/app/real_data/RUNS_MICROBIOME/${run_id}-run_info.csv" \
        --fields /app/init_db/required_fields.json
    
    docker-compose run --rm \
        -v "$(pwd)/../real_data:/app/real_data:ro" \
        loader python /app/upload_CSV.py \
        --host db --port 5432 --db illuqcdb --user postgres --password postgres \
        --table sequencing_qc --csv "/app/real_data/RUNS_MICROBIOME/${run_id}-sequencing_qc.csv" \
        --fields /app/init_db/required_fields.json
done
