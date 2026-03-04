import streamlit as st
import pandas as pd
import altair as alt
import plotly.express as px

from db import get_engine
import queries
from constants import COLUMN_LABELS, METRIC_LABEL_MAP

st.set_page_config(page_title="NGS Protocols", layout="wide")

engine = get_engine()

sequencing_qc_df = queries.get_runs_with_chemistry_protocols(engine)

metrics_df = queries.get_sequencing_metrics(engine)

metrics_df["metric_label"] = metrics_df["metric_name"].fillna(metrics_df["metric_id"])
metrics_df["metric_label"] = metrics_df["metric_label"].replace(METRIC_LABEL_MAP)

# Build a lookup: metric_label → platform_id (from qc_metric_definitions)
metric_platform_lookup = (
    metrics_df[["metric_label", "metric_platform_id"]]
    .drop_duplicates("metric_label")
    .set_index("metric_label")["metric_platform_id"]
    .to_dict()
)

metrics_pivot = (
    metrics_df.pivot_table(
        index=["run_id", "day_id"],
        columns="metric_label",
        values="value_number",
        aggfunc="first",
    )
    .reset_index()
)

sequencing_qc_df = sequencing_qc_df.merge(
    metrics_pivot,
    on=["run_id", "day_id"],
    how="left",
)

if sequencing_qc_df.empty:
    st.warning("No sequencing data found in the database.")
    st.stop()

# Select box for run_description selection
selected_run_description = st.selectbox("Select a Protocol", sequencing_qc_df['run_description'].unique())

# Filter sequencing qc data based on selected run description
filtered_sequencing_qc_df = sequencing_qc_df[sequencing_qc_df['run_description'] == selected_run_description]

if filtered_sequencing_qc_df.empty:
    st.info("No runs found for the selected protocol.")
    st.stop()

# Change column names to more user-friendly names for the metric selection dropdown
filtered_sequencing_qc_df = filtered_sequencing_qc_df.rename(columns=COLUMN_LABELS)


left_column, middle_column, right_column = st.columns([3, 2, 5])

with left_column:
    # Get total number of runs for the selected run description
    total_runs = filtered_sequencing_qc_df['Run ID'].nunique()
    st.metric("Total Runs Sequenced", total_runs, border=True)
    st.metric("Total Samples Sequenced", filtered_sequencing_qc_df['Number of Samples'].sum(), border=True)

with middle_column:
    # Create barplot of number of runs per instrument model for the selected run description
    runs_per_instrument_model = filtered_sequencing_qc_df['Instrument Name'].value_counts().reset_index()
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
    all_metrics_columns = [
        col
        for col in metrics_pivot.columns
        if col not in {"run_id", "day_id"}
    ]

    # Filter metrics to those matching the protocol's platform(s)
    protocol_platforms = filtered_sequencing_qc_df["Platform"].dropna().unique().tolist()
    metrics_columns = [
        col for col in all_metrics_columns
        if metric_platform_lookup.get(col) in (*protocol_platforms, None)
    ]

    metrics_agg = {metric: "mean" for metric in metrics_columns if metric in filtered_sequencing_qc_df.columns}
    metrics_agg["Run ID"] = "size"

    mean_metrics = (
        filtered_sequencing_qc_df.groupby(["Flowcell Name", "Reagent Kit Name"])
        .agg(metrics_agg)
        .reset_index()
        .rename(columns={"Run ID": "Number of Runs"})
    )

    mean_metrics = mean_metrics.rename(
        columns={
            **{metric: f"Mean {metric}" for metric in metrics_columns},
        }
    )
    st.dataframe(mean_metrics, use_container_width=True, hide_index=True)

st.subheader("Explore sequencing metrics over time")

left_column, right_column = st.columns([1, 3])

with left_column:
    # Change column names to more user-friendly names for the metric selection dropdown
    metrics_cols = [
        "Number of Cycles",
        *[metric for metric in metrics_columns if metric in filtered_sequencing_qc_df.columns],
    ]

    # Select box for instrument model selection
    selected_instrument_model = st.selectbox("Select an Instrument Model", filtered_sequencing_qc_df['Instrument Model'].unique())
    
    # Filter data based on selected instrument model and flowcell and reagent kit combination
    filtered_instrument_df = filtered_sequencing_qc_df[(filtered_sequencing_qc_df['Instrument Model'] == selected_instrument_model)].copy()

    # Show flowcell name and reagent kit name for selection instead of sequencing chemistry id
    filtered_instrument_df['flowcell_reagent_combination'] = filtered_instrument_df['Flowcell Name'] + " + " + filtered_instrument_df['Reagent Kit Name']

    # Select box for flowcell and reagent kit combination selection
    chemistry_options = ["All"] + sorted(filtered_instrument_df['flowcell_reagent_combination'].unique().tolist())
    selected_chemistry = st.selectbox("Select a Flowcell and Reagent Kit Combination", chemistry_options)

    # Filter data based on selected instrument model and flowcell and reagent kit combination
    if selected_chemistry == "All":
        filtered_chemistry_df = filtered_instrument_df.copy()
    else:
        filtered_chemistry_df = filtered_instrument_df[(filtered_instrument_df['flowcell_reagent_combination'] == selected_chemistry)]
    
    metrics_options = st.selectbox(
      "Select a Metric to plot:",
        metrics_cols,
        index=None,
        placeholder="Select metric...",
    )

    # Year range slider
    if filtered_chemistry_df.empty:
        plot_df = filtered_chemistry_df
    else:
        date_col = pd.to_datetime(filtered_chemistry_df["Day ID"])
        min_year = int(date_col.dt.year.min())
        max_year = int(date_col.dt.year.max())

        if min_year < max_year:
            year_range = st.slider(
                "Year range:",
                min_value=min_year,
                max_value=max_year,
                value=(min_year, max_year),
            )
            plot_df = filtered_chemistry_df[
                date_col.dt.year.between(year_range[0], year_range[1])
            ]
        else:
            plot_df = filtered_chemistry_df


with right_column:
    if metrics_options:
        # Create line chart for the selected metric over time, colored by chemistry
        color_enc = alt.Color(
            'flowcell_reagent_combination:N',
            legend=alt.Legend(title="Chemistry"),
        )

        x_enc = alt.X('Day ID:T', title='Date')

        fig_line = alt.Chart(plot_df).mark_line().encode(
            x=x_enc,
            y=alt.Y(f'{metrics_options}:Q', title=metrics_options.replace('_', ' ').title()),
            color=color_enc,
        ) + alt.Chart(plot_df).mark_point(size=60).encode(
            x=x_enc,
            y=alt.Y(f'{metrics_options}:Q'),
            color=color_enc,
        )

        st.altair_chart(fig_line, use_container_width=True)

# st.dataframe(filtered_sequencing_qc_df.sort_values(by='day_id'), use_container_width=True)
