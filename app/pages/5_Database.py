import os
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine

# DB connection info from environment or docker-compose
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_NAME = os.getenv("DB_NAME", "illuqcdb")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")

st.set_page_config(page_title="IlluQC Dashboard", layout="wide")
st.title("IlluQC Database Dashboard")

@st.cache_resource
def get_engine():
    return create_engine(
        f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
        pool_pre_ping=True,
    )

# Helper to run a query and return a DataFrame
def run_query(sql, **params):
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql_query(sql, conn, params=params)

# Sidebar controls
tab = st.sidebar.radio("Select view", [
    "Samples", "Runs", "Instruments", "Library", "Protocols", "Day", "Extraction QC", "Library QC", "Sequencing QC", "Bioinfo Analyses QC", "Schema Metadata"
])

if tab == "Samples":
    st.header("Samples")
    df = run_query("SELECT * FROM samples")
    st.dataframe(df)

elif tab == "Runs":
    st.header("Runs")
    df = run_query("SELECT * FROM runs")
    st.dataframe(df)

elif tab == "Instruments":
    st.header("Instruments")
    df = run_query("SELECT * FROM instruments")
    st.dataframe(df)

elif tab == "Library":
    st.header("Library")
    df = run_query("SELECT * FROM library")
    st.dataframe(df)

elif tab == "Protocols":
    st.header("Protocols")
    df = run_query("SELECT * FROM protocols")
    st.dataframe(df)

elif tab == "Day":
    st.header("Day Table (Calendar)")
    df = run_query("SELECT * FROM day ORDER BY day_id DESC LIMIT 100")
    st.dataframe(df)

elif tab == "Extraction QC":
    st.header("Extraction QC")
    df = run_query("SELECT * FROM extraction_qc ORDER BY day_id DESC LIMIT 100")
    st.dataframe(df)
    st.line_chart(df.set_index("day_id")["concentration"]) if not df.empty else st.info("No data.")

elif tab == "Library QC":
    st.header("Library QC")
    df = run_query("SELECT * FROM library_qc ORDER BY day_id DESC LIMIT 100")
    st.dataframe(df)
    st.line_chart(df.set_index("day_id")["concentration"]) if not df.empty else st.info("No data.")

elif tab == "Sequencing QC":
    st.header("Sequencing QC")
    df = run_query("SELECT * FROM sequencing_qc ORDER BY day_id DESC LIMIT 100")
    st.dataframe(df)
    if not df.empty:
        st.line_chart(df.set_index("day_id")["q30"])
        st.line_chart(df.set_index("day_id")["yield"])
    else:
        st.info("No data.")

elif tab == "Bioinfo Analyses QC":
    st.header("Sample Bioinfo Analyses QC")
    df = run_query("SELECT * FROM sample_bioinfo_analyses_qc ORDER BY day_id DESC LIMIT 100")
    st.dataframe(df)
    if not df.empty:
        st.line_chart(df.set_index("day_id")["mean_coverage"])
        st.line_chart(df.set_index("day_id")["percent_on_target_reads"])
    else:
        st.info("No data.")

elif tab == "Schema Metadata":
    st.header("Schema Metadata")
    df = run_query("SELECT * FROM schema_metadata")
    st.dataframe(df)

st.markdown("---")
st.caption(f"Connected to {DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
