
import streamlit as st
import pandas as pd
import plotly.express as px

from db import get_engine
import queries

engine = get_engine()

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

platforms_df = queries.get_platforms(engine)
platform_options = ["All platforms"] + platforms_df["platform_id"].dropna().tolist()
platform_option = st.selectbox(
    "Select Platform:",
    platform_options,
    index=0,
    placeholder="Select platform...",
    key="selected_platform",
)


if option == "All years":
    runs_df = queries.get_runs_with_instruments(engine)
else:
    runs_df = queries.get_runs_with_instruments(engine, year=option)

if platform_option != "All platforms":
    runs_df = runs_df[runs_df["platform_id"] == platform_option]
   
left_column, middle_column, right_column = st.columns(3)

# Runs sequenced in the selected year
if not runs_df.empty:
    with left_column:
        total_runs = runs_df['run_id'].nunique()
        st.metric("Total Runs Sequenced", total_runs, border=True)

    with middle_column:
        # Samples sequenced in the selected year
        total_samples = runs_df['num_samples'].sum()
        st.metric("Total Samples Sequenced", total_samples, border=True)

    with right_column:
        # samples analysed in the selected year
        num_samples_analysed = 0
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

else:
    st.info("No runs found for the selected year.")

