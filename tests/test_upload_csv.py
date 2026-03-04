"""Unit tests for upload_CSV.py.

All database interactions are mocked so no running PostgreSQL instance
is required.  Run with:

    python -m pytest tests/test_upload_csv.py -v
"""

import csv
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest import mock

import pytest

# Make the app directory importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))
from psycopg2 import sql
import upload_CSV as uut  # unit-under-test


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_csv(tmp_path):
    """Create a helper that writes a CSV and returns its path."""
    def _write(filename, rows, fieldnames=None):
        path = tmp_path / filename
        if fieldnames is None:
            fieldnames = list(rows[0].keys()) if rows else []
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
        return str(path)
    return _write


@pytest.fixture
def fields_json(tmp_path):
    """Create a required-fields JSON file and return its path."""
    def _write(mapping):
        path = tmp_path / "fields.json"
        with open(path, "w") as f:
            json.dump(mapping, f)
        return str(path)
    return _write


@pytest.fixture
def mock_conn():
    """Return a mock psycopg2 connection with a usable cursor context manager."""
    conn = mock.MagicMock()
    cursor = mock.MagicMock()
    conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)
    return conn, cursor


# ---------------------------------------------------------------------------
# table_exists
# ---------------------------------------------------------------------------

class TestTableExists:
    def test_returns_true_when_table_found(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchone.return_value = (True,)
        assert uut.table_exists(conn, "runs") is True

    def test_returns_false_when_table_missing(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchone.return_value = (False,)
        assert uut.table_exists(conn, "nonexistent") is False


# ---------------------------------------------------------------------------
# get_table_columns
# ---------------------------------------------------------------------------

class TestGetTableColumns:
    def test_returns_column_names(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchall.return_value = [("run_id",), ("day_id",), ("metric_id",)]
        result = uut.get_table_columns(conn, "sequencing_qc_metrics")
        assert result == ["run_id", "day_id", "metric_id"]

    def test_returns_empty_list_for_no_columns(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchall.return_value = []
        assert uut.get_table_columns(conn, "empty_table") == []


# ---------------------------------------------------------------------------
# load_required_map
# ---------------------------------------------------------------------------

class TestLoadRequiredMap:
    def test_loads_valid_json(self, fields_json):
        mapping = {"runs": ["run_id", "day_id"], "samples": ["sample_id"]}
        path = fields_json(mapping)
        result = uut.load_required_map(path)
        assert result == mapping

    def test_raises_on_non_dict(self, tmp_path):
        path = tmp_path / "bad.json"
        with open(path, "w") as f:
            json.dump(["not", "a", "dict"], f)
        with pytest.raises(ValueError, match="JSON object"):
            uut.load_required_map(str(path))

    def test_raises_on_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            uut.load_required_map(str(tmp_path / "missing.json"))


# ---------------------------------------------------------------------------
# normalize_long_format_row
# ---------------------------------------------------------------------------

class TestNormalizeLongFormatRow:
    def test_empty_string_becomes_none(self):
        row = {"run_id": "R1", "value_number": ""}
        result = uut.normalize_long_format_row(row)
        assert result["value_number"] is None

    def test_none_stays_none(self):
        row = {"run_id": "R1", "value_number": None}
        result = uut.normalize_long_format_row(row)
        assert result["value_number"] is None

    def test_numeric_string_unchanged(self):
        row = {"run_id": "R1", "value_number": "42.5"}
        result = uut.normalize_long_format_row(row)
        assert result["value_number"] == "42.5"

    def test_returns_same_dict(self):
        row = {"run_id": "R1", "value_number": "1.0"}
        assert uut.normalize_long_format_row(row) is row


# ---------------------------------------------------------------------------
# main() — integration-style tests with mocked DB
# ---------------------------------------------------------------------------

class TestMain:
    """Test the CLI main() function end-to-end with mocked psycopg2."""

    def _run_main(self, args):
        """Call main() with the given sys.argv list."""
        with mock.patch("sys.argv", ["upload_CSV.py"] + args):
            return uut.main()

    def test_missing_csv_returns_2(self, fields_json):
        path = fields_json({"my_table": ["col1"]})
        rc = self._run_main([
            "--db", "testdb", "--table", "my_table",
            "--csv", "/nonexistent/file.csv",
            "--fields", path,
        ])
        assert rc == 2

    def test_missing_fields_file_returns_2(self, tmp_csv):
        csv_path = tmp_csv("data.csv", [{"col1": "a"}])
        rc = self._run_main([
            "--db", "testdb", "--table", "my_table",
            "--csv", csv_path,
            "--fields", "/nonexistent/fields.json",
        ])
        assert rc == 2

    def test_table_not_in_fields_returns_2(self, tmp_csv, fields_json):
        csv_path = tmp_csv("data.csv", [{"col1": "a"}])
        fpath = fields_json({"other_table": ["col1"]})
        rc = self._run_main([
            "--db", "testdb", "--table", "my_table",
            "--csv", csv_path,
            "--fields", fpath,
        ])
        assert rc == 2

    @mock.patch("upload_CSV.psycopg2")
    def test_nonexistent_table_returns_2(self, mock_pg, tmp_csv, fields_json):
        csv_path = tmp_csv("data.csv", [{"run_id": "R1", "day_id": "2026-01-01"}])
        fpath = fields_json({"my_table": ["run_id", "day_id"]})

        # Mock connection
        conn = mock.MagicMock()
        mock_pg.connect.return_value = conn
        cursor = mock.MagicMock()
        conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=cursor)
        conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)
        # table_exists → False
        cursor.fetchone.return_value = (False,)

        rc = self._run_main([
            "--db", "testdb", "--table", "my_table",
            "--csv", csv_path,
            "--fields", fpath,
        ])
        assert rc == 2

    @mock.patch("upload_CSV.psycopg2")
    def test_missing_required_column_in_csv_returns_2(self, mock_pg, tmp_csv, fields_json):
        # CSV has col1 but required fields demand col1 + col2
        csv_path = tmp_csv("data.csv", [{"col1": "a"}])
        fpath = fields_json({"my_table": ["col1", "col2"]})

        conn = mock.MagicMock()
        mock_pg.connect.return_value = conn
        cursor = mock.MagicMock()
        conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=cursor)
        conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)
        # table_exists → True
        cursor.fetchone.return_value = (True,)
        # get_table_columns
        cursor.fetchall.return_value = [("col1",), ("col2",)]

        rc = self._run_main([
            "--db", "testdb", "--table", "my_table",
            "--csv", csv_path,
            "--fields", fpath,
        ])
        assert rc == 2

    @mock.patch("upload_CSV.psycopg2")
    def test_successful_insert(self, mock_pg, tmp_csv, fields_json):
        csv_path = tmp_csv("data.csv", [
            {"run_id": "R1", "day_id": "2026-01-01"},
            {"run_id": "R2", "day_id": "2026-01-02"},
        ])
        fpath = fields_json({"my_table": ["run_id", "day_id"]})

        conn = mock.MagicMock()
        mock_pg.connect.return_value = conn
        cursor = mock.MagicMock()
        conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=cursor)
        conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)

        # table_exists → True
        cursor.fetchone.return_value = (True,)
        # get_table_columns → run_id, day_id
        cursor.fetchall.return_value = [("run_id",), ("day_id",)]

        # psycopg2.sql needs a real connection for as_string(); patch it
        # so that Composed.as_string() returns a plain string.
        with mock.patch("upload_CSV.sql") as mock_sql:
            mock_composed = mock.MagicMock()
            mock_composed.as_string.return_value = "INSERT INTO my_table (run_id, day_id) VALUES (%s, %s)"
            mock_sql.SQL.return_value.format.return_value = mock_composed
            mock_sql.Identifier = sql.Identifier
            mock_sql.Placeholder = sql.Placeholder

            rc = self._run_main([
                "--db", "testdb", "--table", "my_table",
                "--csv", csv_path,
                "--fields", fpath,
            ])
        assert rc == 0
        # executemany should have been called with the 2 rows
        cursor.executemany.assert_called_once()
        batch = cursor.executemany.call_args[0][1]
        assert len(batch) == 2

    @mock.patch("upload_CSV.psycopg2")
    def test_strict_mode_rejects_extra_columns(self, mock_pg, tmp_csv, fields_json):
        csv_path = tmp_csv("data.csv", [{"col1": "a", "extra_col": "b"}])
        fpath = fields_json({"my_table": ["col1"]})

        conn = mock.MagicMock()
        mock_pg.connect.return_value = conn
        cursor = mock.MagicMock()
        conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=cursor)
        conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)
        cursor.fetchone.return_value = (True,)
        # Table only has col1
        cursor.fetchall.return_value = [("col1",)]

        rc = self._run_main([
            "--db", "testdb", "--table", "my_table",
            "--csv", csv_path,
            "--fields", fpath,
            "--strict",
        ])
        assert rc == 2

    @mock.patch("upload_CSV.psycopg2")
    def test_extra_columns_ignored_without_strict(self, mock_pg, tmp_csv, fields_json):
        csv_path = tmp_csv("data.csv", [{"col1": "a", "extra_col": "b"}])
        fpath = fields_json({"my_table": ["col1"]})

        conn = mock.MagicMock()
        mock_pg.connect.return_value = conn
        cursor = mock.MagicMock()
        conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=cursor)
        conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)
        cursor.fetchone.return_value = (True,)
        cursor.fetchall.return_value = [("col1",)]

        rc = self._run_main([
            "--db", "testdb", "--table", "my_table",
            "--csv", csv_path,
            "--fields", fpath,
        ])
        assert rc == 0
