"""Centralised SQL queries for the IlluQC Streamlit app.

Every public function accepts a SQLAlchemy *engine* (or connection) as its
first argument, plus optional filter parameters, and returns a DataFrame.

Results are cached with ``@st.cache_data(ttl=300)`` so that repeated
Streamlit reruns do not hit the database unnecessarily.
"""

import pandas as pd
import streamlit as st
from sqlalchemy import text


# ---------------------------------------------------------------------------
# Cache TTL (seconds) – shared across all queries
# ---------------------------------------------------------------------------

_TTL = 300  # 5 minutes


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _read(engine, sql, **params):
    """Execute *sql* with optional named params and return a DataFrame."""
    with engine.connect() as conn:
        return pd.read_sql_query(text(sql), conn, params=params)


# ---------------------------------------------------------------------------
# Platforms
# ---------------------------------------------------------------------------

@st.cache_data(ttl=_TTL, show_spinner=False)
def get_platforms(_engine):
    """Distinct platform_ids present in sequencing_run."""
    return _read(
        _engine,
        "SELECT DISTINCT platform_id FROM sequencing_run ORDER BY platform_id",
    )


# ---------------------------------------------------------------------------
# Sequencing runs (with instrument info)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=_TTL, show_spinner=False)
def get_runs_with_instruments(_engine, *, year=None):
    """Sequencing runs joined with instruments.

    Parameters
    ----------
    year : int, str or None
        If given, restrict to runs whose day_id falls in that calendar year.
    """
    if year is None:
        sql = """
            SELECT *
            FROM sequencing_run srq
            JOIN instruments inst ON srq.instrument_id = inst.instrument_id
        """
        df = _read(_engine, sql)
    else:
        sql = """
            SELECT *
            FROM sequencing_run srq
            JOIN instruments inst ON srq.instrument_id = inst.instrument_id
            WHERE srq.day_id BETWEEN :start AND :end
        """
        df = _read(_engine, sql, start=f"{year}-01-01", end=f"{year}-12-31")

    return df.loc[:, ~df.columns.duplicated()]


@st.cache_data(ttl=_TTL, show_spinner=False)
def get_runs_with_chemistry(_engine):
    """Sequencing runs joined with instruments AND sequencing_chemistry."""
    sql = """
        SELECT srq.*, sc.*, inst.instrument_model, inst.instrument_name
        FROM sequencing_run srq
        JOIN sequencing_chemistry sc
          ON srq.sequencing_chemistry_id = sc.sequencing_chemistry_id
        JOIN instruments inst
          ON srq.instrument_id = inst.instrument_id
    """
    df = _read(_engine, sql)
    return df.loc[:, ~df.columns.duplicated()]


@st.cache_data(ttl=_TTL, show_spinner=False)
def get_runs_with_chemistry_protocols(_engine):
    """Sequencing runs joined with instruments, chemistry – for Protocols page."""
    sql = """
        SELECT srq.*, inst.instrument_model, inst.instrument_name,
               sc.flowcell_name, sc.reagent_kit_name
        FROM sequencing_run srq
        JOIN instruments inst ON srq.instrument_id = inst.instrument_id
        JOIN sequencing_chemistry sc
          ON srq.sequencing_chemistry_id = sc.sequencing_chemistry_id
    """
    df = _read(_engine, sql)
    return df.loc[:, ~df.columns.duplicated()]


# ---------------------------------------------------------------------------
# Sequencing QC metrics
# ---------------------------------------------------------------------------

@st.cache_data(ttl=_TTL, show_spinner=False)
def get_sequencing_metrics(_engine):
    """All sequencing QC metric values with their definitions."""
    sql = """
        SELECT sqm.run_id, sqm.day_id, sqm.metric_id, sqm.value_number,
               qmd.metric_name, qmd.unit, qmd.platform_id AS metric_platform_id
        FROM sequencing_qc_metrics sqm
        LEFT JOIN qc_metric_definitions qmd ON sqm.metric_id = qmd.metric_id
    """
    return _read(_engine, sql)


@st.cache_data(ttl=_TTL, show_spinner=False)
def get_sequencing_metrics_recent(_engine, *, limit=200):
    """Most recent sequencing QC metric values (for the Database explorer)."""
    sql = """
        SELECT sqm.run_id, sqm.day_id, sqm.metric_id, sqm.value_number,
               qmd.metric_name, qmd.unit, qmd.platform_id AS metric_platform_id
        FROM sequencing_qc_metrics sqm
        LEFT JOIN qc_metric_definitions qmd ON sqm.metric_id = qmd.metric_id
        ORDER BY sqm.day_id DESC
        LIMIT :lim
    """
    return _read(_engine, sql, lim=limit)


# ---------------------------------------------------------------------------
# Bioinfo analyses
# ---------------------------------------------------------------------------

@st.cache_data(ttl=_TTL, show_spinner=False)
def get_bioinfo_analyses(_engine, *, year=None):
    """Sample-level bioinfo analyses QC, optionally filtered by year."""
    if year is None:
        sql = "SELECT * FROM sample_bioinfo_analyses_qc"
        return _read(_engine, sql)
    sql = """
        SELECT * FROM sample_bioinfo_analyses_qc
        WHERE day_id BETWEEN :start AND :end
    """
    return _read(_engine, sql, start=f"{year}-01-01", end=f"{year}-12-31")




# ---------------------------------------------------------------------------
# Simple dimension-table helpers (Database explorer page)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=_TTL, show_spinner=False)
def get_table(_engine, table: str, *, order_by=None, limit=None):
    """Read an entire table with optional ORDER BY and LIMIT.

    Only allows table names from an explicit allow-list to prevent SQL
    injection.
    """
    allowed = {
        "samples",
        "instruments",
        "library",
        "protocols",
        "day",
        "extraction_qc",
        "library_qc",
        "sequencing_run",
        "sequencing_qc_metrics",
        "qc_metric_definitions",
        "sequencing_platforms",
        "sequencing_chemistry",
        "sample_bioinfo_analyses_qc",
        "schema_metadata",
    }
    if table not in allowed:
        raise ValueError(f"Table '{table}' is not in the allow-list.")

    sql = f"SELECT * FROM {table}"
    if order_by:
        sql += f" ORDER BY {order_by}"
    if limit:
        sql += f" LIMIT {limit}"
    return _read(_engine, sql)
