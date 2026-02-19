#!/usr/bin/env python3
"""Small utility to load a CSV file into a SQLite table.
"""

import argparse
import csv
import json
import logging
import os
import psycopg2
from psycopg2 import sql
import sys


def table_exists(conn, table):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name=%s)",
            (table,)
        )
        return cur.fetchone()[0]


def get_table_columns(conn, table):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name=%s",
            (table,)
        )
        return [r[0] for r in cur.fetchall()]


def load_required_map(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("required columns file must be a JSON object {table: [cols...]}")
    return data

    ap = argparse.ArgumentParser(description="Load CSV into PostgreSQL table.")
    ap.add_argument("--host", default="db", help="Postgres host")
    ap.add_argument("--port", default="5432", help="Postgres port")
    ap.add_argument("--db", required=True, help="Postgres database name")
    ap.add_argument("--user", default="postgres", help="Postgres user")
    ap.add_argument("--password", default="postgres", help="Postgres password")
    ap.add_argument("--table", required=True, help="Target table name")
    ap.add_argument("--csv", required=True, help="CSV file path")
    ap.add_argument("--fields", required=True, help="JSON file mapping table, required fields list")
    ap.add_argument(
        "--strict",
        action="store_true",
        help="Fail if CSV includes columns not present in the table (default: ignore extra CSV columns).",
    )
    ap.add_argument("--batch-size", type=int, default=1000, help="Batch size for inserts (default: 1000)")
    ap.add_argument("--log", default="INFO", help="Logging level (DEBUG, INFO, WARNING, ERROR)")
    args = ap.parse_args()

    logging.basicConfig(level=args.log.upper(), format='%(levelname)s:%(message)s')

    csv_path = os.path.abspath(args.csv)
    fields_path = os.path.abspath(args.fields)

    logging.info(f"CSV path: {csv_path}")
    logging.info(f"Fields path: {fields_path}")

    if not os.path.exists(csv_path):
        logging.error("CSV not found: %s", csv_path)
        return 2
    if not os.path.exists(fields_path):
        logging.error("Required fields file not found: %s", fields_path)
        return 2

    required_map = load_required_map(fields_path)
    required_cols = required_map.get(args.table)
    logging.info(f"Required columns for table '{args.table}': {required_cols}")
    if required_cols is None:
        logging.error("No required columns defined for table %r in %s", args.table, fields_path)
        return 2

    conn = psycopg2.connect(
        host=args.host,
        port=args.port,
        dbname=args.db,
        user=args.user,
        password=args.password
    )
    logging.info("Connected to database: %s", args.db)
    try:
        if not table_exists(conn, args.table):
            logging.error("Table does not exist: %s", args.table)
            return 2

        table_cols = get_table_columns(conn, args.table)
        table_set = set(table_cols)
        logging.info(f"Table columns: {table_cols}")

        # Ensure required columns exist in the table
        missing_in_table = [c for c in required_cols if c not in table_set]
        if missing_in_table:
            logging.error(
                "Required columns %s declared for table %s but not present in the table schema",
                missing_in_table,
                args.table,
            )
            return 2

        # Read CSV headers quickly to decide which columns to insert
        with open(csv_path, "r", newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []
        logging.info(f"CSV columns: {headers}")

        # Check required columns exist in CSV
        missing_required = [c for c in required_cols if c not in headers]
        if missing_required:
            logging.error("CSV missing required columns for %s: %s", args.table, missing_required)
            return 2

        # Identify extra CSV columns
        extra = [h for h in headers if h not in table_set]
        if extra and args.strict:
            logging.error("CSV contains columns not in table %s: %s", args.table, extra)
            return 2

        # Only insert columns present in table
        insert_cols = [h for h in headers if h in table_set]
        if not insert_cols:
            logging.error("No CSV columns match table columns")
            return 2

        cols_sql = sql.SQL(', ').join(map(sql.Identifier, insert_cols))
        placeholders = sql.SQL(', ').join(sql.Placeholder() * len(insert_cols))
        table_sql = sql.Identifier(args.table)
        insert_sql = sql.SQL("INSERT INTO {table} ({fields}) VALUES ({values}) ON CONFLICT DO NOTHING").format(
            table=table_sql,
            fields=cols_sql,
            values=placeholders
        )

        # Insert rows in batches
        inserted = 0
        batch_size = args.batch_size
        batch = []
        with open(csv_path, "r", newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader):
                values = [row[col] for col in insert_cols]
                logging.debug(f"Row {idx}: {values}")
                batch.append(values)
                if len(batch) >= batch_size:
                    try:
                        with conn.cursor() as cur:
                            cur.executemany(insert_sql.as_string(conn), batch)
                        conn.commit()
                        inserted += len(batch)
                        batch.clear()
                    except Exception as e:
                        logging.error(f"Failed to insert batch ending at row {idx}: {e}")
            if batch:
                try:
                    with conn.cursor() as cur:
                        cur.executemany(insert_sql.as_string(conn), batch)
                    conn.commit()
                    inserted += len(batch)
                except Exception as e:
                    logging.error(f"Failed to insert final batch: {e}")

        logging.info("Loaded %d rows into '%s' from %s", inserted, args.table, os.path.basename(csv_path))
        logging.info("Inserted columns: %s", insert_cols)
        if extra and not args.strict:
            logging.warning("Ignored extra CSV columns (not in table): %s", extra)

        return 0

    finally:
        conn.close()


def main():
    ap = argparse.ArgumentParser(description="Load CSV into PostgreSQL table.")
    ap.add_argument("--host", default="db", help="Postgres host")
    ap.add_argument("--port", default="5432", help="Postgres port")
    ap.add_argument("--db", required=True, help="Postgres database name")
    ap.add_argument("--user", default="postgres", help="Postgres user")
    ap.add_argument("--password", default="postgres", help="Postgres password")
    ap.add_argument("--table", required=True, help="Target table name")
    ap.add_argument("--csv", required=True, help="CSV file path")
    ap.add_argument("--fields", required=True, help="JSON file mapping table, required fields list")
    ap.add_argument(
        "--strict",
        action="store_true",
        help="Fail if CSV includes columns not present in the table (default: ignore extra CSV columns).",
    )
    ap.add_argument("--batch-size", type=int, default=1000, help="Batch size for inserts (default: 1000)")
    ap.add_argument("--log", default="INFO", help="Logging level (DEBUG, INFO, WARNING, ERROR)")
    args = ap.parse_args()

    logging.basicConfig(level=args.log.upper(), format='%(levelname)s:%(message)s')

    csv_path = os.path.abspath(args.csv)
    fields_path = os.path.abspath(args.fields)

    logging.info(f"CSV path: {csv_path}")
    logging.info(f"Fields path: {fields_path}")

    if not os.path.exists(csv_path):
        logging.error("CSV not found: %s", csv_path)
        return 2
    if not os.path.exists(fields_path):
        logging.error("Required fields file not found: %s", fields_path)
        return 2

    required_map = load_required_map(fields_path)
    required_cols = required_map.get(args.table)
    logging.info(f"Required columns for table '{args.table}': {required_cols}")
    if required_cols is None:
        logging.error("No required columns defined for table %r in %s", args.table, fields_path)
        return 2

    conn = psycopg2.connect(
        host=args.host,
        port=args.port,
        dbname=args.db,
        user=args.user,
        password=args.password
    )
    logging.info("Connected to database: %s", args.db)
    try:
        if not table_exists(conn, args.table):
            logging.error("Table does not exist: %s", args.table)
            return 2

        table_cols = get_table_columns(conn, args.table)
        table_set = set(table_cols)
        logging.info(f"Table columns: {table_cols}")

        # Ensure required columns exist in the table
        missing_in_table = [c for c in required_cols if c not in table_set]
        if missing_in_table:
            logging.error(
                "Required columns %s declared for table %s but not present in the table schema",
                missing_in_table,
                args.table,
            )
            return 2

        # Read CSV headers quickly to decide which columns to insert
        with open(csv_path, "r", newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []
        logging.info(f"CSV columns: {headers}")

        # Check required columns exist in CSV
        missing_required = [c for c in required_cols if c not in headers]
        if missing_required:
            logging.error("CSV missing required columns for %s: %s", args.table, missing_required)
            return 2

        # Identify extra CSV columns
        extra = [h for h in headers if h not in table_set]
        if extra and args.strict:
            logging.error("CSV contains columns not in table %s: %s", args.table, extra)
            return 2

        # Only insert columns present in table
        insert_cols = [h for h in headers if h in table_set]
        if not insert_cols:
            logging.error("No CSV columns match table columns")
            return 2

        cols_sql = sql.SQL(', ').join(map(sql.Identifier, insert_cols))
        placeholders = sql.SQL(', ').join(sql.Placeholder() * len(insert_cols))
        table_sql = sql.Identifier(args.table)
        insert_sql = sql.SQL("INSERT INTO {table} ({fields}) VALUES ({values}) ON CONFLICT DO NOTHING").format(
            table=table_sql,
            fields=cols_sql,
            values=placeholders
        )

        # Insert rows in batches
        inserted = 0
        batch_size = args.batch_size
        batch = []
        with open(csv_path, "r", newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader):
                values = [row[col] for col in insert_cols]
                logging.debug(f"Row {idx}: {values}")
                batch.append(values)
                if len(batch) >= batch_size:
                    try:
                        with conn.cursor() as cur:
                            cur.executemany(insert_sql.as_string(conn), batch)
                        conn.commit()
                        inserted += len(batch)
                        batch.clear()
                    except Exception as e:
                        logging.error(f"Failed to insert batch ending at row {idx}: {e}")
            if batch:
                try:
                    with conn.cursor() as cur:
                        cur.executemany(insert_sql.as_string(conn), batch)
                    conn.commit()
                    inserted += len(batch)
                except Exception as e:
                    logging.error(f"Failed to insert final batch: {e}")

        logging.info("Loaded %d rows into '%s' from %s", inserted, args.table, os.path.basename(csv_path))
        logging.info("Inserted columns: %s", insert_cols)
        if extra and not args.strict:
            logging.warning("Ignored extra CSV columns (not in table): %s", extra)

        return 0

    finally:
        conn.close()

if __name__ == "__main__":
    raise SystemExit(main())
