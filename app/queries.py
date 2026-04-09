"""Centralised SQL queries for the IlluQC Streamlit app.

Every public function accepts a SQLAlchemy *engine* (or connection) as its
first argument, plus optional filter parameters, and returns a DataFrame.
"""

import pandas as pd
from sqlalchemy import text


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

def get_platforms(engine):
    """Distinct platform_ids present in sequencing_run."""
    return _read(
        engine,
        "SELECT DISTINCT platform_id FROM sequencing_run ORDER BY platform_id",
    )


# ---------------------------------------------------------------------------
# Sequencing runs (with instrument info)
# ---------------------------------------------------------------------------

def get_runs_with_instruments(engine, *, year=None):
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
        df = _read(engine, sql)
    else:
        sql = """
            SELECT *
            FROM sequencing_run srq
            JOIN instruments inst ON srq.instrument_id = inst.instrument_id
            WHERE srq.day_id BETWEEN :start AND :end
        """
        df = _read(engine, sql, start=f"{year}-01-01", end=f"{year}-12-31")

    return df.loc[:, ~df.columns.duplicated()]


def get_runs_with_chemistry(engine):
    """Sequencing runs joined with instruments, chemistry name AND attributes.

    The ``sequencing_chemistry`` table provides the human-readable
    ``chemistry_name``.  Long-format chemistry attributes (per *run_id*)
    are pivoted into extra columns using the ``attribute_name`` from the
    definitions table.  LEFT JOINs ensure runs without chemistry data
    are still returned.
    """
    sql = """
        SELECT srq.*,
               inst.instrument_model, inst.instrument_name,
               sc.chemistry_name,
               cad.attribute_name,
               sca.attribute_value
        FROM sequencing_run srq
        LEFT JOIN sequencing_chemistry sc
          ON srq.sequencing_chemistry_id = sc.sequencing_chemistry_id
        LEFT JOIN instruments inst
          ON srq.instrument_id = inst.instrument_id
        LEFT JOIN sequencing_chemistry_attributes sca
          ON srq.run_id = sca.run_id
        LEFT JOIN chemistry_attribute_definitions cad
          ON sca.attribute_id = cad.attribute_id
    """
    df = _read(engine, sql)
    df = df.loc[:, ~df.columns.duplicated()]
    # Pivot long-format attributes into wide columns
    if "attribute_name" in df.columns and not df["attribute_name"].isna().all():
        run_cols = [c for c in df.columns if c not in ("attribute_name", "attribute_value")]
        attrs = (
            df[["run_id", "day_id", "attribute_name", "attribute_value"]]
            .drop_duplicates()
            .pivot_table(
                index=["run_id", "day_id"],
                columns="attribute_name",
                values="attribute_value",
                aggfunc="first",
            )
            .reset_index()
        )
        base = df[run_cols].drop_duplicates(subset=["run_id", "day_id"])
        df = base.merge(attrs, on=["run_id", "day_id"], how="left")
    else:
        df = df.drop(columns=["attribute_name", "attribute_value"], errors="ignore")
    return df


def get_runs_with_chemistry_protocols(engine):
    """Sequencing runs joined with instruments, chemistry – for Protocols page.

    Returns the same pivoted attributes as ``get_runs_with_chemistry``."""
    return get_runs_with_chemistry(engine)


# ---------------------------------------------------------------------------
# Sequencing QC metrics
# ---------------------------------------------------------------------------

def get_sequencing_metrics(engine):
    """All sequencing QC metric values with their definitions."""
    sql = """
        SELECT sqm.run_id, sqm.day_id, sqm.metric_id, sqm.value_number,
               qmd.metric_name, qmd.display_label, qmd.unit,
               qmd.platform_id AS metric_platform_id
        FROM sequencing_qc_metrics sqm
        LEFT JOIN qc_metric_definitions qmd ON sqm.metric_id = qmd.metric_id
    """
    return _read(engine, sql)


# ---------------------------------------------------------------------------
# Sample QC metrics
# ---------------------------------------------------------------------------

def get_sample_qc_metrics_for_run(engine, run_id):
    """All per-sample QC metrics for a given run, joined with definitions.

    Parameters
    ----------
    run_id : str
        The sequencing run identifier.
    """
    sql = """
        SELECT sqm.sample_id, sqm.run_id, sqm.read,
               sqm.metric_id, sqm.value_number,
               qmd.metric_name, qmd.display_label, qmd.unit
        FROM sample_qc_metrics sqm
        LEFT JOIN qc_metric_definitions qmd ON sqm.metric_id = qmd.metric_id
        WHERE sqm.run_id = :run_id
        ORDER BY sqm.sample_id, sqm.read, qmd.metric_name
    """
    return _read(engine, sql, run_id=run_id)



def get_sample_qc_sample_ids(engine):
    """Return distinct sample_id values that have sample QC data, sorted."""
    sql = """
        SELECT DISTINCT sample_id
        FROM sample_qc_metrics
        ORDER BY sample_id
    """
    return _read(engine, sql)


def get_sample_qc_metrics_for_sample(engine, sample_id):
    """All QC metrics for a given sample across all runs, with run info.

    Parameters
    ----------
    sample_id : str
        The sample identifier to look up.
    """
    sql = """
        SELECT sqm.sample_id, sqm.run_id, sqm.read,
               sqm.metric_id, sqm.value_number,
               qmd.metric_name, qmd.display_label, qmd.unit,
               sr.day_id, sr.run_description, sr.platform_id,
               inst.instrument_model, inst.instrument_name,
               l.library_id, l.library_name, l.library_type,
               s.sex, s.virtual_panel
        FROM sample_qc_metrics sqm
        LEFT JOIN qc_metric_definitions qmd ON sqm.metric_id = qmd.metric_id
        JOIN sequencing_run sr ON sqm.run_id = sr.run_id
        LEFT JOIN instruments inst ON sr.instrument_id = inst.instrument_id
        LEFT JOIN sample_library sl
          ON sqm.sample_id = sl.sample_id AND sqm.run_id = sl.run_id
        LEFT JOIN library l ON sl.library_id = l.library_id
        LEFT JOIN samples s ON sqm.sample_id = s.sample_id
        WHERE sqm.sample_id = :sample_id
        ORDER BY sr.day_id DESC, sqm.run_id, sqm.read, qmd.metric_name
    """
    return _read(engine, sql, sample_id=sample_id)


def get_sample_qc_metrics_by_library(engine, library_id, run_id):
    """All per-sample QC metrics for samples sharing a library in a run.

    Used to build the density/distribution chart on the Samples page so the
    user can see where their sample sits relative to the library cohort.

    Parameters
    ----------
    library_id : str
        The library identifier (from the ``library`` table).
    run_id : str
        The sequencing run identifier.
    """
    sql = """
        SELECT sqm.sample_id, sqm.run_id, sqm.read,
               sqm.metric_id, sqm.value_number,
               qmd.metric_name, qmd.display_label, qmd.unit
        FROM sample_qc_metrics sqm
        JOIN sample_library sl
          ON sqm.sample_id = sl.sample_id AND sqm.run_id = sl.run_id
        LEFT JOIN qc_metric_definitions qmd ON sqm.metric_id = qmd.metric_id
        WHERE sl.library_id = :library_id
          AND sqm.run_id     = :run_id
        ORDER BY sqm.sample_id, sqm.read, qmd.metric_name
    """
    return _read(engine, sql, library_id=library_id, run_id=run_id)


# ---------------------------------------------------------------------------
# Metric display-label maps (driven by qc_metric_definitions table)
# ---------------------------------------------------------------------------

def get_metric_label_maps(engine):
    """Build metric display-label maps from qc_metric_definitions.

    Returns
    -------
    run_label_map : dict
        ``{metric_name: display_label}`` for scope='run' metrics.
    sample_label_map : dict
        ``{metric_name: display_label}`` for scope='sample' metrics.
    """
    sql = """
        SELECT metric_id, metric_name, display_label, scope, platform_id
        FROM qc_metric_definitions
        WHERE display_label IS NOT NULL
    """
    df = _read(engine, sql)

    run_rows = df[df["scope"] == "run"]
    sample_rows = df[df["scope"] == "sample"]

    run_label_map = dict(zip(run_rows["metric_name"], run_rows["display_label"]))
    sample_label_map = dict(zip(sample_rows["metric_name"], sample_rows["display_label"]))

    return run_label_map, sample_label_map
