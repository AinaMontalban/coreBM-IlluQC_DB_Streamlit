import argparse
import os
import pandas as pd
import psycopg2
from psycopg2 import sql
import logging

DB_HOST = os.environ.get("POSTGRES_HOST", "db")
DB_PORT = os.environ.get("POSTGRES_PORT", "5432")
DB_NAME = os.environ.get("POSTGRES_DB", "illuqcdb")
DB_USER = os.environ.get("POSTGRES_USER", "postgres")
DB_PASS = os.environ.get("POSTGRES_PASSWORD", "postgres")

TABLES = {
    'samples': ['sample_id', 'sample_name', 'collection_date', 'project_id'],
    'projects': ['project_id', 'project_name', 'description'],
    'qc_metrics': ['qc_id', 'sample_id', 'metric_name', 'metric_value', 'measured_at'],
    'users': ['user_id', 'username', 'email', 'role'],
    'runs': ['run_id', 'run_name', 'run_date', 'instrument'],
}

    logging.info(f"Reading CSV: {csv_path}")
    df = pd.read_csv(csv_path)
    logging.info(f"CSV columns: {list(df.columns)}")
    missing = set(columns) - set(df.columns)
    if missing:
        logging.error(f"CSV {csv_path} missing columns for table {table}: {missing}")
        raise ValueError(f"CSV {csv_path} missing columns for table {table}: {missing}")
    with conn.cursor() as cur:
        for idx, row in df.iterrows():
            insert = sql.SQL("INSERT INTO {table} ({fields}) VALUES ({values}) ON CONFLICT DO NOTHING;").format(
                table=sql.Identifier(table),
                fields=sql.SQL(',').join(map(sql.Identifier, columns)),
                values=sql.SQL(',').join(sql.Placeholder() * len(columns))
            )
            values = [row[col] for col in columns]
            logging.debug(f"Row {idx}: {values}")
            try:
                cur.execute(insert, values)
            except Exception as e:
                logging.error(f"Failed to insert row {idx}: {e}")
    conn.commit()
    logging.info(f"Finished loading {len(df)} rows into {table}")

    parser = argparse.ArgumentParser(description="Load CSVs into IlluQC DB.")
    parser.add_argument('--log', default='INFO', help='Logging level (DEBUG, INFO, WARNING, ERROR)')
    for table in TABLES:
        parser.add_argument(f"--{table}", nargs="*", help=f"CSV(s) for {table}")
    args = parser.parse_args()
    logging.basicConfig(level=args.log.upper(), format='%(levelname)s:%(message)s')
    logging.info(f"Connecting to DB: host={DB_HOST}, port={DB_PORT}, db={DB_NAME}, user={DB_USER}")
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASS
    )
    for table, columns in TABLES.items():
        csv_files = getattr(args, table)
        if csv_files:
            for csv_path in csv_files:
                logging.info(f"Loading {csv_path} into {table}...")
                load_csv_to_table(conn, table, csv_path, columns)
    conn.close()
    logging.info("All CSV loading complete.")

if __name__ == "__main__":
    main()
