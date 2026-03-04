#!/usr/bin/env python3
"""Load long-format sequencing metrics into PostgreSQL.

Expected CSV columns: run_id, day_id, metric_id, value_number
"""

import argparse
import csv
import logging
import os
from typing import Dict, Iterable, List

import psycopg2
from psycopg2 import sql


REQUIRED_COLUMNS = ["run_id", "day_id", "metric_id", "value_number"]
TABLE_NAME = "sequencing_qc_metrics"


def table_exists(conn, table: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name=%s)",
            (table,),
        )
        return cur.fetchone()[0]


def get_table_columns(conn, table: str) -> List[str]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name=%s",
            (table,),
        )
        return [r[0] for r in cur.fetchall()]


def normalize_row(row: Dict[str, str]) -> Dict[str, str | None]:
    if row.get("value_number") in {"", None}:
        row["value_number"] = None
    return row


def iter_rows(csv_path: str) -> Iterable[Dict[str, str | None]]:
    with open(csv_path, "r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            yield normalize_row(row)


def load_metrics(conn, csv_path: str, batch_size: int) -> int:
    table_cols = get_table_columns(conn, TABLE_NAME)
    table_set = set(table_cols)

    missing = [col for col in REQUIRED_COLUMNS if col not in table_set]
    if missing:
        raise RuntimeError(
            f"Table '{TABLE_NAME}' is missing required columns: {missing}"
        )

    cols_sql = sql.SQL(", ").join(map(sql.Identifier, REQUIRED_COLUMNS))
    placeholders = sql.SQL(", ").join(sql.Placeholder() * len(REQUIRED_COLUMNS))
    insert_sql = sql.SQL(
        "INSERT INTO {table} ({fields}) VALUES ({values}) ON CONFLICT DO NOTHING"
    ).format(table=sql.Identifier(TABLE_NAME), fields=cols_sql, values=placeholders)

    inserted = 0
    batch: List[List[str | None]] = []

    for idx, row in enumerate(iter_rows(csv_path)):
        values = [row.get(col) for col in REQUIRED_COLUMNS]
        batch.append(values)
        if len(batch) >= batch_size:
            with conn.cursor() as cur:
                cur.executemany(insert_sql.as_string(conn), batch)
            conn.commit()
            inserted += len(batch)
            logging.debug("Inserted batch ending at row %s", idx)
            batch.clear()

    if batch:
        with conn.cursor() as cur:
            cur.executemany(insert_sql.as_string(conn), batch)
        conn.commit()
        inserted += len(batch)

    return inserted


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Load long-format sequencing metrics into PostgreSQL."
    )
    parser.add_argument("--host", default="db", help="Postgres host")
    parser.add_argument("--port", default="5432", help="Postgres port")
    parser.add_argument("--db", required=True, help="Postgres database name")
    parser.add_argument("--user", default="postgres", help="Postgres user")
    parser.add_argument("--password", default="postgres", help="Postgres password")
    parser.add_argument("--csv", required=True, help="CSV file path")
    parser.add_argument("--batch-size", type=int, default=1000, help="Insert batch size")
    parser.add_argument("--log", default="INFO", help="Logging level")
    args = parser.parse_args()

    logging.basicConfig(level=args.log.upper(), format="%(levelname)s:%(message)s")

    csv_path = os.path.abspath(args.csv)
    if not os.path.exists(csv_path):
        logging.error("CSV not found: %s", csv_path)
        return 2

    with open(csv_path, "r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        headers = reader.fieldnames or []

    missing_headers = [col for col in REQUIRED_COLUMNS if col not in headers]
    if missing_headers:
        logging.error("CSV missing required columns: %s", missing_headers)
        return 2

    conn = psycopg2.connect(
        host=args.host,
        port=args.port,
        dbname=args.db,
        user=args.user,
        password=args.password,
    )
    logging.info("Connected to database: %s", args.db)
    try:
        if not table_exists(conn, TABLE_NAME):
            logging.error("Table does not exist: %s", TABLE_NAME)
            return 2
        inserted = load_metrics(conn, csv_path, args.batch_size)
        logging.info("Loaded %d rows into '%s'", inserted, TABLE_NAME)
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
