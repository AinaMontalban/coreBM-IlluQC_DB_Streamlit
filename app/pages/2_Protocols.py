import streamlit as st
import pandas as pd
import altair as alt
import plotly.express as px

from sqlalchemy import create_engine

st.set_page_config(page_title="NGS Protocols", layout="wide")

# Connect to PostgreSQL directly
DB_HOST = "db"
DB_PORT = "5432"
DB_NAME = "illuqcdb"
DB_USER = "postgres"
DB_PASSWORD = "postgres"
engine = create_engine(f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

# Get sequencing qc data and run info data
sequencing_qc_df = pd.read_sql_query(
            """
            SELECT * FROM sequencing_qc sqc
            JOIN instruments inst ON sqc.instrument_id = inst.instrument_id
            JOIN sequencing_chemistry sc ON sqc.sequencing_chemistry_id = sc.sequencing_chemistry_id
            JOIN runs r ON sqc.run_id = r.run_id;
            """,
            engine
        )

# Remove duplicated columns from instruments table
sequencing_qc_df = sequencing_qc_df.loc[:, ~sequencing_qc_df.columns.duplicated()]

# Select box for run_description selection
selected_run_description = st.selectbox("Select a Protocol", sequencing_qc_df['run_description'].unique())

# Filter sequencing qc data based on selected run description
filtered_sequencing_qc_df = sequencing_qc_df[sequencing_qc_df['run_description'] == selected_run_description]
#st.dataframe(filtered_sequencing_qc_df.sort_values(by='day_id'), use_container_width=True)

# Change column names to more user-friendly names for the metric selection dropdown
columns_names_dict={
    "cluster_density": "Cluster Density (K/mm²)",
    "num_cycles": "Number of Cycles",
    "cluster_pf": "% PF Clusters",
    "q30": "% Q30 Reads",
    "yield": "Yield (Gb)",
    "percent_phix_aligned": "% PhiX Aligned"
}
filtered_sequencing_qc_df = filtered_sequencing_qc_df.rename(columns=columns_names_dict)


left_column, middle_column, right_column = st.columns([3, 2, 5])

with left_column:
    # Get total number of runs for the selected run description
    total_runs = filtered_sequencing_qc_df['run_id'].nunique()
    st.metric("Total Runs Sequenced", total_runs, border=True)
    st.metric("Total Samples Sequenced", filtered_sequencing_qc_df['num_samples'].sum(), border=True)

with middle_column:
    # Create barplot of number of runs per instrument model for the selected run description
    runs_per_instrument_model = filtered_sequencing_qc_df['instrument_name'].value_counts().reset_index()
    runs_per_instrument_model.columns = ['instrument_name', 'num_runs']

    with st.spinner("Wait for it...", show_time=True):
        st.write("Number of runs per sequencer:")
        # Display a pie plot of the number of runs per instrument model for the selected run description
        fig_pie = px.pie(runs_per_instrument_model, names='instrument_name', values='num_runs', width=200, height=200)
        # Move the legend to the right of the plot and make it horizontal
        fig_pie.update_layout(legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5))
        fig_pie.update_layout(margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig_pie)

with right_column:
    st.write("Number of runs per flowcell and reagent kit:")

    # Get mean metric values for each flowcell part number and reagent kit part number and count the number of runs 
    mean_metrics = filtered_sequencing_qc_df.groupby(['flowcell_name', 'reagent_kit_name']).agg(
                num_runs=('run_id', 'size'),
                cluster_density_mean=('Cluster Density (K/mm²)', 'mean'),
                cluster_pf_mean=('% PF Clusters', 'mean'),
                q30_mean=('% Q30 Reads', 'mean'),
                yield_value_mean=('Yield (Gb)', 'mean'),
                percent_phix_aligned_mean=('% PhiX Aligned', 'mean')
    ).reset_index()

    mean_metrics = mean_metrics.rename(columns={
        'flowcell_name': 'Flowcell Name',
        'reagent_kit_name': 'Reagent Kit Name',
        'num_runs': 'Number of Runs',
        'cluster_density_mean': 'Mean Cluster Density (K/mm²)',
        'cluster_pf_mean': 'Mean % PF Clusters',
        'q30_mean': 'Mean % Q30 Reads',
        'yield_value_mean': 'Mean Yield (Gb)',
        'percent_phix_aligned_mean': 'Mean % PhiX Aligned'
    })
    st.dataframe(mean_metrics, use_container_width=True, hide_index=True)

st.subheader("Explore sequencing metrics over time")

left_column, right_column = st.columns([1, 3])

with left_column:
    # Change column names to more user-friendly names for the metric selection dropdown
    metrics_cols = ['Cluster Density (K/mm²)', 'Number of Cycles', '% PF Clusters', '% Q30 Reads', 'Yield (Gb)', '% PhiX Aligned']

    # Select box for instrument model selection
    selected_instrument_model = st.selectbox("Select an Instrument Model", filtered_sequencing_qc_df['instrument_model'].unique())
    
    # Filter data based on selected instrument model and flowcell and reagent kit combination
    filtered_instrument_df = filtered_sequencing_qc_df[(filtered_sequencing_qc_df['instrument_model'] == selected_instrument_model)].copy()

    # Show flowcell name and reagent kit name for selection instead of sequencing chemistry id
    filtered_instrument_df['flowcell_reagent_combination'] = filtered_instrument_df['flowcell_name'] + " + " + filtered_instrument_df['reagent_kit_name']

    # Select box for flowcell and reagent kit combination selection
    selected_chemistry = st.selectbox("Select a Flowcell and Reagent Kit Combination", filtered_instrument_df['flowcell_reagent_combination'].unique())

    # Filter data based on selected instrument model and flowcell and reagent kit combination
    filtered_chemistry_df = filtered_instrument_df[(filtered_instrument_df['flowcell_reagent_combination'] == selected_chemistry)]
    
    metrics_options = st.selectbox(
      "Select a Metric to plot:",
        metrics_cols,
        index=None,
        placeholder="Select metric...",
    )

    # Select box for coloring the line chart by instrument name
    # Radio button to color by instrument model id or run description
    #color_by_instrument_name = st.radio(
    #    "Color by:",
    #    ('instrument_name')
    #)


with right_column:
    if metrics_options:
        # Create line chart for the selected metric over time, colored by run description and add points to the line chart
        fig_line = alt.Chart(filtered_chemistry_df).mark_line().encode(
            x='day_id:T',
            y=alt.Y(f'{metrics_options}:Q', title=metrics_options.replace('_', ' ').title())
            ) + alt.Chart(filtered_chemistry_df).mark_point(size=60).encode(
            x='day_id:T',
            y=alt.Y(f'{metrics_options}:Q')#,
            #color=color_by_instrument_name if color_by_instrument_name else alt.value('blue')
        )

        st.altair_chart(fig_line, use_container_width=True)







        #fig_line = px.line(combination_df, x='day_id', y=metrics_options, color='run_description', title=f"{metrics_options.replace('_', ' ').title()} over Time for {flowcell_reagent_combination}")
        #st.plotly_chart(fig_line)

# st.dataframe(filtered_sequencing_qc_df.sort_values(by='day_id'), use_container_width=True)
