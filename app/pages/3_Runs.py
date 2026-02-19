
import streamlit as st
import pandas as pd
import altair as alt
from sqlalchemy import create_engine
import plotly.express as px

st.set_page_config(page_title="Runs", layout="wide")

# use column names except for 'run_id', 'day_id', 'instrument_id', 'flowcell_part_number', 'reagent_kit_part_number', 'num_samples'
st.write("# Runs")

# Connect to PostgreSQL directly
DB_HOST = "db"
DB_PORT = "5432"
DB_NAME = "illuqcdb"
DB_USER = "postgres"
DB_PASSWORD = "postgres"
engine = create_engine(f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

# Create better column names for the runs table
columns_names_dict={
    "run_id": "Run ID",
    "run_description": "Run Description",
    "day_id": "Day ID",
    "instrument_id": "Instrument ID",
    "instrument_model": "Instrument Model",
    "instrument_name": "Instrument Name",
    "sequencing_chemistry_id": "Sequencing Chemistry ID",
    "flowcell_part_number": "Flowcell Part Number",
    "flowcell_name": "Flowcell Name",
    "reagent_kit_part_number": "Reagent Kit Part Number",
    "reagent_kit_name": "Reagent Kit Name",
    "num_samples": "Number of Samples",
    "cluster_density": "Cluster Density (K/mm²)",
    "num_cycles": "Number of Cycles",
    "cluster_pf": "% PF Clusters",
    "q30": "% Q30 Reads",
    "yield": "Yield (Gb)",
    "percent_phix_aligned": "% PhiX Aligned"}

metrics_columns = ['Cluster Density (K/mm²)', '% PF Clusters', '% Q30 Reads', 'Yield (Gb)', '% PhiX Aligned']


# query all runs from the database and join with sequencing chemistry and instruments tables to get run metadata, sequencing chemistry info and instrument info for all runs
runs_df = pd.read_sql_query(
    """
    SELECT sqc.*, sc.*, inst.instrument_model, inst.instrument_name, r.run_description
    FROM sequencing_qc sqc
    JOIN sequencing_chemistry sc ON sqc.sequencing_chemistry_id = sc.sequencing_chemistry_id
    JOIN instruments inst ON sqc.instrument_id = inst.instrument_id
    JOIN runs r ON sqc.run_id = r.run_id
    """,
    engine
)

# remove duplicated columns from instruments table
runs_df = runs_df.loc[:, ~runs_df.columns.duplicated()]

# change column names in the database query
runs_df = runs_df.rename(columns=columns_names_dict)

# Define runs_ids
runs_ids = runs_df[['Run ID']].drop_duplicates().sort_values(by='Run ID', ascending=False)

left_column, right_column = st.columns(2)

with left_column:
    run_option = st.selectbox(
        "Select Run ID:",
        runs_ids,
        index=None,
        placeholder="Write run ID...",
    )

    if run_option is None:
        st.write("Please select a Run ID to see the details.")
    elif run_option not in runs_ids['Run ID'].values:
        st.write("Run ID not found in the database. Please select a valid Run ID.")
    else:        
        # query sequencing_qc and join with sequencing_chemistry and instruments tables to get sequencing qc metrics and instrument info for the selected run
        selected_run_df = pd.read_sql_query(
            f"""
            SELECT sqc.*, sc.*, inst.instrument_model, inst.instrument_name, r.run_description
            FROM sequencing_qc sqc
            JOIN sequencing_chemistry sc ON sqc.sequencing_chemistry_id = sc.sequencing_chemistry_id
            JOIN instruments inst ON sqc.instrument_id = inst.instrument_id
            JOIN runs r ON sqc.run_id = r.run_id
            WHERE sqc.run_id = '{run_option}'
            """,
            engine
        )

        # remove duplicated columns from instruments table
        selected_run_df = selected_run_df.loc[:, ~selected_run_df.columns.duplicated()]
        # change column names in the database query
        selected_run_df = selected_run_df.rename(columns=columns_names_dict)
        # transpose the dataframe to have metrics as rows and values in a single column
        #selected_run_df = selected_run_df.melt(id_vars=['Run ID'], var_name='Metric', value_name='Value').drop(columns=['Run ID'])

        # Display run metadata as text
        container = st.container(border=True)
        container.write(f"**Run Description:** {selected_run_df['Run Description'].values[0]}")
        container.write(f"**Day ID:** {selected_run_df.loc[selected_run_df['Run ID'] == run_option, 'Day ID'].values[0]}")
        container.write(f"**Instrument Name:** {selected_run_df.loc[selected_run_df['Run ID'] == run_option, 'Instrument Name'].values[0]}")
        container.write(f"**Flowcell:** {selected_run_df.loc[selected_run_df['Run ID'] == run_option, 'Flowcell Name'].values[0]}")
        container.write(f"**Reagent Kit:** {selected_run_df.loc[selected_run_df['Run ID'] == run_option, 'Reagent Kit Name'].values[0]}")
        container.write(f"**Number of Samples:** {selected_run_df.loc[selected_run_df['Run ID'] == run_option, 'Number of Samples'].values[0]}")
        container.write(f"**Number of Cycles:** {selected_run_df.loc[selected_run_df['Run ID'] == run_option, 'Number of Cycles'].values[0]}")

        st.subheader(f"Sequencing metrics")
        # select only the metrics columns to display in the table
        df_metrics = selected_run_df[metrics_columns].copy()
        # transpose the dataframe to have metrics as rows and values in a single column
        df_metrics = df_metrics.melt(var_name='Metric', value_name='Value')
         # round the values to 2 decimals
        df_metrics['Value'] = df_metrics['Value'].round(2)
         # display the metrics in a table
        st.dataframe(df_metrics, use_container_width=True, hide_index=True)

with right_column:
    metric_options = st.selectbox(
        "Select Metric to plot:",
        metrics_columns,
        index=None,
        placeholder="Select metric...",
    )

    if metric_options is not None and run_option is not None:
        # find runs with the same run description as the selected run
        df_same_description = runs_df[runs_df['Run Description'] == selected_run_df['Run Description'].values[0]]
        # find runs with the same instrument model and sequencing chemistry as the selected run
        df_same_instrument_chemistry = df_same_description[(df_same_description['Instrument Model'] == selected_run_df['Instrument Model'].values[0]) & (df_same_description['Sequencing Chemistry ID'] == selected_run_df['Sequencing Chemistry ID'].values[0])]

        selected_value = runs_df.loc[runs_df['Run ID'] == run_option, metric_options].values[0]
        
        
        st.subheader(f"Distribution plot for {metric_options}")
        # density plot to check distribution of the selected metric
        metric = metric_options

        df_plot = df_same_instrument_chemistry[[metric]].copy()
        df_plot[metric] = pd.to_numeric(df_plot[metric], errors="coerce")
        df_plot = df_plot.dropna(subset=[metric])


        # Create density plot using Altair
        # Add a line for the selected run value
        density_chart = (
            alt.Chart(df_plot)
            .transform_density(metric, as_=[metric, "density"])
            .mark_area()
            .encode(
                x=alt.X(f"{metric}:Q", title=metric),
                y="density:Q",
            )
        )

        vline = (
            alt.Chart(pd.DataFrame({metric: [selected_value]}))
            .mark_rule(color="red", strokeWidth=2)
            .encode(
                x=alt.X(f"{metric}:Q"),
                tooltip=[alt.Tooltip(f"{metric}:Q", title="Selected run")]
            )
        )

        chart = density_chart + vline
        st.altair_chart(chart, use_container_width=True)

        # Write captions to know with how many runs the distribution is being compared and what the red line means
        st.caption(f"The distribution is based on {len(df_plot)} runs with the same instrument model and sequencing chemistry as the selected run.The red line indicates the value of the selected metric for the run {run_option}.")

# Get all samples associated with the selected run
if st.button("Check Samples QC") and run_option is not None and run_option in runs_ids['Run ID'].values:

    # Query samples bioinfo analyses qc for the selected run and join with samples table to get sample metadata
    samples_bioinfo_df = pd.read_sql_query(
    f"""
    SELECT sbaq.*, s.sex, s.virtual_panel
    FROM sample_bioinfo_analyses_qc sbaq
    JOIN samples s ON sbaq.sample_id = s.sample_id
    WHERE sbaq.run_id = '{run_option}'
    """,
    engine
    )

    num_samples_in_run = len(samples_bioinfo_df)
    st.metric(label="Number of Samples in this Run", value=num_samples_in_run)
    
    # Display a bar chart with total reads per sample in this run
    st.subheader("Primary Analysis: Total Reads per Sample")
    # Melt the dataframe for better plotting
    samples_bioinfo_melted_df = samples_bioinfo_df.melt(id_vars=['sample_id'], value_vars=['total_reads_r1', 'total_reads_r2'], var_name='Read Type', value_name='Total Reads')
    st.bar_chart(data=samples_bioinfo_melted_df, x='sample_id', y='Total Reads', color='Read Type', use_container_width=True)

    st.subheader("Secondary Analysis:")
    # Display a table with mean_coverage and cov_20x per sample in this run
    samples_secondary_analysis_df = samples_bioinfo_df[['sample_id', 'sex', 'virtual_panel', 'mean_coverage', 'cov_20x', 'cov_38x', 'percent_on_target_reads', 'coverage_uniformity']]
    st.dataframe(samples_secondary_analysis_df.rename(columns={
        'sample_id': 'Sample ID',
        'sex': 'Reported Sex',
        'virtual_panel': 'Virtual Panel',
        'mean_coverage': 'Mean Coverage',
        'cov_20x': 'Coverage 20x (%)',
        'cov_38x': 'Coverage 38x (%)',
        'percent_on_target_reads': 'Percent On Target Reads (%)',
        'coverage_uniformity': 'Coverage Uniformity (%)'
    }), use_container_width=True)
