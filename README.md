# IlluQC Database Project (Streamlit + PostgreSQL)

This project provides a reproducible environment for managing and visualizing IlluQC data using PostgreSQL, Streamlit, and Docker Compose.

## Features
- PostgreSQL database with IlluQC schema (see `init_db/IlluQC_Database_schema_postgres.sql`)
- Streamlit dashboard for interactive data exploration (`app/streamlit_app.py`)
- Loader scripts and CSV import support
- Docker Compose orchestration for easy setup

## Quick Start

### 1. Build and Start the Stack
```sh
docker-compose up --build
```
- This starts Postgres and Streamlit (default: http://localhost:8501).

### 2. Initialize the Database Schema
- The schema is defined in `init_db/IlluQC_Database_schema_postgres.sql`.
- On first run, the schema is loaded automatically. To reapply manually:
```sh
docker-compose exec db psql -U postgres -d exampledb -f /docker-entrypoint-initdb.d/IlluQC_Database_schema_postgres.sql
```

### 3. Load Data from CSV Files

```sh
docker-compose run --rm \
  -v "$(pwd)/../real_data:/app/real_data:ro" \
  loader python /app/upload_CSV.py \
  --host db --port 5432 --db illuqcdb --user postgres --password postgres \
  --table instruments --csv /app/real_data/instruments/IlluQC_instruments.csv \
  --fields /app/init_db/required_fields.json

docker-compose run --rm \
        -v "$(pwd)/../real_data:/app/real_data:ro" \
        loader python /app/upload_CSV.py \
        --host db --port 5432 --db illuqcdb --user postgres --password postgres \
        --table sequencing_chemistry --csv "/app/real_data/sequencing_chemistry.csv" \
        --fields /app/init_db/required_fields.json


local_folder="/Users/amontalban/HCB-Work/Doctorat/P005-multiplatform/"
common_folder="/real_data/RUNS_4"

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


```


Check size: docker-compose exec db psql -U postgres -d illuqcdb -c "SELECT pg_size_pretty(pg_database_size('illuqcdb')) AS database_size;"

The `required_fields.json` file in `init_db/` defines required columns for each table.
You can use this script for any table by changing the `--table` and `--csv` arguments.


### 4. Explore Data in Streamlit (with Pages)
- Open http://localhost:8501 in your browser.
- Use the sidebar to navigate Streamlit pages scripts (e.g., `app/pages/1_Summary.py`).
- Pages scripts connect to PostgreSQL using Streamlit's SQL connection:
	- Make sure your `.streamlit/secrets.toml` is configured for the illuqcdb Postgres connection.
	- Example secrets.toml:
		```toml
		[illuqc_db]
		url = "postgresql://postgres:postgres@db:5432/illuqcdb"
		```
- You can add more scripts in `app/pages/` for custom dashboards and analyses.

### 5. Back Up the Database
```sh
mkdir -p backups
docker-compose exec db pg_dump -U postgres -d illuqcdb | gzip > backups/illuqcdb-$(date +%Y%m%d_%H%M%S).sql.gz

```

### 6. Restore a Backup
```sh
docker-compose exec db psql -U postgres -c "CREATE DATABASE illuqcdb;"
gunzip -c backups/illuqcdb-YYYYMMDD_HHMMSS.sql.gz | docker-compose exec -T db psql -U postgres -d illuqcdb
```

## Test Data

The `test_data/` directory contains a generator and a loader script that create a fully populated database for development and demo purposes — no real data required.

### What is generated

| Table                    | Rows  | Description                                                                |
|--------------------------|-------|----------------------------------------------------------------------------|
| `instruments`            | 3     | MiSeq, NextSeq 2000, Ion S5 XL                                            |
| `sequencing_chemistry`   | 3     | One kit per instrument                                                     |
| `library`                | 3     | Twist WES, Agilent WES, AmpliSeq Panel                                    |
| `samples`                | 84    | 24 per run (12 are shared between TEST_RUN_001 and TEST_RUN_004)           |
| `sample_library`         | 96    | Per-run sample↔library assignments                                        |
| `sequencing_run`         | 4     | 2 Illumina MiSeq, 1 NextSeq, 1 ThermoFisher                              |
| `sequencing_qc_metrics`  | 20    | 5 run-level metrics × 4 runs                                              |
| `sample_qc_metrics`      | 840   | 5 FastQC metrics × 2 reads × 24 samples × 3 Illumina + 5 × 1 × 24 × 1 TF|

TEST_RUN_004 intentionally **reuses 12 samples from TEST_RUN_001** so the Samples page shows a tabbed layout when inspecting those shared samples.

### Step 1 — Generate the CSV files

```sh
cd coreBM-IlluQC_DB_Streamlit
python test_data/generate_test_data.py
```

This writes all CSVs into `test_data/`. The generator uses a fixed random seed (`42`) for reproducibility. You can pass `--outdir /other/path` to change the output directory.

### Step 2 — Start a clean database

```sh
docker compose down -v          # remove existing DB volume
docker compose up -d db         # start fresh PostgreSQL
sleep 3                         # wait for readiness
```

### Step 3 — Bulk-load the test data

```sh
bash test_data/bulk_load_test_data.sh
```

The script loads tables in the correct dependency order:

1. **Dimension tables** — `instruments`, `sequencing_chemistry`, `library`, `samples`, `sample_library`
2. **Per-run data** (auto-detected via glob) — `sequencing_run`, `sequencing_qc_metrics`, `sample_qc_metrics`

### Step 4 — Start Streamlit and verify

```sh
docker compose up -d streamlit
```

Open http://localhost:8501 and navigate the pages. To verify row counts:

```sh
docker compose exec db psql -U postgres -d illuqcdb -c \
  "SELECT 'instruments' AS tbl, count(*) FROM instruments
   UNION ALL SELECT 'samples', count(*) FROM samples
   UNION ALL SELECT 'library', count(*) FROM library
   UNION ALL SELECT 'sample_library', count(*) FROM sample_library
   UNION ALL SELECT 'sequencing_run', count(*) FROM sequencing_run
   UNION ALL SELECT 'sequencing_qc_metrics', count(*) FROM sequencing_qc_metrics
   UNION ALL SELECT 'sample_qc_metrics', count(*) FROM sample_qc_metrics
   ORDER BY tbl;"
```

### Adding more test runs

Edit `RUNS` in `test_data/generate_test_data.py`. To create a run that shares samples with an existing run, add `reuse_from` and `reuse_count` keys:

```python
{
    "run_id": "TEST_RUN_005",
    # ... other fields ...
    "reuse_from": "TEST_RUN_001",  # reuse first N samples from this run
    "reuse_count": 6,
}
```

Then regenerate and reload:

```sh
python test_data/generate_test_data.py
docker compose down -v && docker compose up -d db && sleep 3
bash test_data/bulk_load_test_data.sh
```

---

## Customization
- Edit `init_db/01_schema_ddl.sql` and `init_db/02_schema_seed.sql` to change the schema.
- Edit or add CSVs in `data/csvs/` for your data.
- Update Streamlit pages in `app/pages/` to change the dashboard or add new visualizations.

## Troubleshooting
- **Port 8501 busy:** Set `STREAMLIT_PORT` in `.env` or export before running compose.
- **CSV not found:** Ensure the file path is correct and the folder is mounted into the container.
- **DB schema missing:** Run the init SQL manually as shown above.
- **Duplicate data:** Loader currently appends; for idempotency, ask for dedup logic.

## Optional Enhancements
- Idempotent shop loading (skip duplicates)
- Dry-run mode for loaders
- Automated backup/restore scripts
- S3 integration for backups

---
