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


Use the advanced loader (`upload_CSV.py`):
```sh
docker-compose run --rm loader python /app/upload_CSV.py \
	--host db --port 5432 --db illuqcdb --user postgres --password postgres \
	--table samples --csv /app/data/csvs/IlluQC_samples.csv \
	--fields /app/init_db/required_fields.json

docker-compose run --rm loader python /app/upload_CSV.py \
	--host db --port 5432 --db illuqcdb --user postgres --password postgres \
	--table instruments --csv /app/data/csvs/IlluQC_instruments.csv \
	--fields /app/init_db/required_fields.json

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

docker-compose run --rm \
	 -v "$(pwd)/../real_data:/app/real_data:ro" \
	loader python /app/upload_CSV.py \
	--host db --port 5432 --db illuqcdb --user postgres --password postgres \
	--table library --csv /app/real_data/library/IlluQC_libraries.csv \
	--fields /app/init_db/required_fields.json

docker-compose run --rm \
	 -v "$(pwd)/../real_data:/app/real_data:ro" \
	loader python /app/upload_CSV.py \
	--host db --port 5432 --db illuqcdb --user postgres --password postgres \
	--table runs --csv /app/real_data/RUNS/R3612_run_info.csv \
	--fields /app/init_db/required_fields.json

docker-compose run --rm \
	 -v "$(pwd)/../real_data:/app/real_data:ro" \
	loader python /app/upload_CSV.py \
	--host db --port 5432 --db illuqcdb --user postgres --password postgres \
	--table sequencing_qc --csv /app/real_data/sequencing_qc/R3612_sequencing_qc.csv \
	--fields /app/init_db/required_fields.json

docker-compose run --rm loader python /app/upload_CSV.py \
	--host db --port 5432 --db illuqcdb --user postgres --password postgres \
	--table sample_bioinfo_analyses_qc --csv /app/data/csvs/IlluQC_sample_bioinfo_analyses_qc.csv \
	--fields /app/init_db/required_fields.json

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

## Customization
- Edit `init_db/IlluQC_Database_schema_postgres.sql` to change the schema.
- Edit or add CSVs in `data/csvs/` for your data.
- Update `app/streamlit_app.py` to change the dashboard or add new visualizations.

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
