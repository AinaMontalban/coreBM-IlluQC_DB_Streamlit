
import streamlit as st
import pandas as pd
import plotly.express as px
import psycopg2
from sqlalchemy import create_engine

# Connect to PostgreSQL directly
DB_HOST = "db"
DB_PORT = "5432"
DB_NAME = "illuqcdb"
DB_USER = "postgres"
DB_PASSWORD = "postgres"
engine = create_engine(f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

# Set page configuration
st.set_page_config(page_title="Activity Summary", layout="wide")

# Add year selector
st.title("Activity Summary")


# Get list of years based on today's date
start_year = 2020
current_year = pd.Timestamp.today().year
year_list = ["All years"] + list(range(current_year, start_year - 1, -1))

# Create a selectbox for year selection
option = st.selectbox(
    "Select Year:",
    year_list,
    index=0,
    placeholder="Select year...",
    key="selected_year",
)


if option == "All years":
    runs_df = pd.read_sql_query(
        f"""
        SELECT *
        FROM sequencing_qc sqc
        JOIN instruments inst ON sqc.instrument_id = inst.instrument_id
        JOIN runs r ON sqc.run_id = r.run_id
        """,
        engine
    )
    runs_df = runs_df.loc[:, ~runs_df.columns.duplicated()]

    sample_bioinfo_analyses_qc = pd.read_sql_query(
        f"""
        SELECT *
        FROM sample_bioinfo_analyses_qc sbaq
        JOIN runs r ON sbaq.run_id = r.run_id
        """,
        engine
    )
else:
    # Query sequencing qc, runs, and instrument info for the selected year
    runs_df = pd.read_sql_query(
        f"""
        SELECT *
        FROM sequencing_qc sqc
        JOIN instruments inst ON sqc.instrument_id = inst.instrument_id
        JOIN runs r ON sqc.run_id = r.run_id
        WHERE sqc.day_id BETWEEN '{option}-01-01' AND '{option}-12-31'
        """,
        engine
    )
    runs_df = runs_df.loc[:, ~runs_df.columns.duplicated()]

    sample_bioinfo_analyses_qc = pd.read_sql_query(
        f"""
        SELECT *
        FROM sample_bioinfo_analyses_qc sbaq
        JOIN runs r ON sbaq.run_id = r.run_id
        WHERE sbaq.day_id BETWEEN '{option}-01-01' AND '{option}-12-31'
        """,
        engine
    )


left_column, middle_column, right_column = st.columns(3)

    # Runs sequenced in the selected year
if not runs_df.empty:
    with left_column:
            total_runs = len(runs_df)
            st.metric("Total Runs Sequenced", total_runs, border=True)

    with middle_column:
            # Samples sequenced in the selected year
            total_samples = runs_df['num_samples'].sum()
            st.metric("Total Samples Sequenced", total_samples, border=True)

    with right_column:
        # samples analysed in the selected year
        num_samples_analysed = sample_bioinfo_analyses_qc['sample_id'].nunique()
        st.metric("Samples Analyzed", num_samples_analysed, border=True)


# count the number of rows
if not runs_df.empty:
        left_column, right_column = st.columns(2)
        with left_column:
            # Prepare data for treemap plot and count number of runs for each run_description
            total_runs_per_run_description = runs_df.groupby('run_description', as_index=False).agg({'run_id': 'size'})
            fig = px.treemap(total_runs_per_run_description, path=['run_description'], values='run_id', title="Protocol Distribution")
            st.plotly_chart(fig)

        with right_column:
            # Create histogram of runs per sequencer
            runs_per_instrument = runs_df['instrument_name'].value_counts()

            fig_bar=px.bar(runs_per_instrument, x=runs_per_instrument.index, y=runs_per_instrument.values, text_auto=True, title="Runs per sequencer")

            # Change x-axis title and y-axis title
            fig_bar.update_layout(xaxis_title="Sequencer", yaxis_title="Number of Runs")

            st.plotly_chart(fig_bar)

        #st.bar_chart(runs_per_instrument)

        # Create histogram of samples analysed per library
        if not sample_bioinfo_analyses_qc.empty:
            st.subheader("Samples Analyzed per Library")
            samples_per_library = sample_bioinfo_analyses_qc['library_id'].value_counts()
            st.bar_chart(samples_per_library)
else:
    st.info("No runs found for the selected year.")

