import pandas as pd
import streamlit as st

from db import get_engine
import queries

st.set_page_config(page_title="IlluQC Dashboard", layout="wide")
st.title("IlluQC Database Dashboard")

engine = get_engine()

# Sidebar controls
tab = st.sidebar.radio("Select view", [
    "Samples",
    "Instruments",
    "Library",
    "Protocols",
    "Day",
    "Extraction QC",
    "Library QC",
    "Sequencing QC",
    "Bioinfo Analyses QC",
    "Schema Metadata",
])

if tab == "Samples":
    st.header("Samples")
    df = queries.get_table(engine, "samples")
    st.dataframe(df)

elif tab == "Instruments":
    st.header("Instruments")
    df = queries.get_table(engine, "instruments")
    st.dataframe(df)

elif tab == "Library":
    st.header("Library")
    df = queries.get_table(engine, "library")
    st.dataframe(df)

elif tab == "Protocols":
    st.header("Protocols")
    df = queries.get_table(engine, "protocols")
    st.dataframe(df)

elif tab == "Day":
    st.header("Day Table (Calendar)")
    df = queries.get_table(engine, "day", order_by="day_id DESC", limit=100)
    st.dataframe(df)

elif tab == "Extraction QC":
    st.header("Extraction QC")
    df = queries.get_table(engine, "extraction_qc", order_by="day_id DESC", limit=100)
    st.dataframe(df)
    st.line_chart(df.set_index("day_id")["concentration"]) if not df.empty else st.info("No data.")

elif tab == "Library QC":
    st.header("Library QC")
    df = queries.get_table(engine, "library_qc", order_by="day_id DESC", limit=100)
    st.dataframe(df)
    st.line_chart(df.set_index("day_id")["concentration"]) if not df.empty else st.info("No data.")

elif tab == "Sequencing QC":
    st.header("Sequencing QC (Core)")
    df = queries.get_table(engine, "sequencing_run", order_by="day_id DESC", limit=100)
    st.dataframe(df)

    st.subheader("Sequencing QC Metrics")
    metrics_df = queries.get_sequencing_metrics_recent(engine, limit=200)
    st.dataframe(metrics_df)

    if not metrics_df.empty:
        metric_options = metrics_df["metric_name"].fillna(metrics_df["metric_id"]).unique().tolist()
        selected_metric = st.selectbox("Metric chart", metric_options, index=0)
        metrics_df["metric_label"] = metrics_df["metric_name"].fillna(metrics_df["metric_id"])
        df_plot = metrics_df[metrics_df["metric_label"] == selected_metric].copy()
        df_plot["value_number"] = pd.to_numeric(df_plot["value_number"], errors="coerce")
        df_plot = df_plot.dropna(subset=["value_number"])
        if not df_plot.empty:
            st.line_chart(df_plot.set_index("day_id")["value_number"])
        else:
            st.info("No numeric values for the selected metric.")
    else:
        st.info("No sequencing metrics found.")

elif tab == "Bioinfo Analyses QC":
    st.header("Sample Bioinfo Analyses QC")
    df = queries.get_bioinfo_analyses(engine)
    st.dataframe(df)
    if not df.empty:
        st.line_chart(df.set_index("day_id")["mean_coverage"])
        st.line_chart(df.set_index("day_id")["percent_on_target_reads"])
    else:
        st.info("No data.")

elif tab == "Schema Metadata":
    st.header("Schema Metadata")
    df = queries.get_table(engine, "schema_metadata")
    st.dataframe(df)

st.markdown("---")
db = st.secrets["postgres"]
st.caption(f"Connected to {db['user']}@{db['host']}:{db['port']}/{db['dbname']}")
