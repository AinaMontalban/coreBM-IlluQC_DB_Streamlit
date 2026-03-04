
import streamlit as st
import pandas as pd
import altair as alt
import plotly.express as px

from db import get_engine
import queries
from constants import COLUMN_LABELS, METRIC_LABEL_MAP

st.set_page_config(page_title="Runs", layout="wide")

# use column names except for 'run_id', 'day_id', 'instrument_id', 'flowcell_part_number', 'reagent_kit_part_number', 'num_samples'
st.write("# Runs")

engine = get_engine()


# query all runs from the database and join with sequencing chemistry and instruments tables to get run metadata, sequencing chemistry info and instrument info for all runs
runs_df = queries.get_runs_with_chemistry(engine)

if runs_df.empty:
    st.warning("No sequencing runs found in the database.")
    st.stop()

metrics_df = queries.get_sequencing_metrics(engine)

# change column names in the database query
runs_df = runs_df.rename(columns=COLUMN_LABELS)

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

runs_with_metrics = runs_df.merge(
    metrics_pivot,
    left_on=["Run ID", "Day ID"],
    right_on=["run_id", "day_id"],
    how="left",
)

metrics_columns = [
    col
    for col in metrics_pivot.columns
    if col not in {"run_id", "day_id"}
]

# Define runs_ids
runs_ids = runs_df[["Run ID", "Day ID"]].drop_duplicates().sort_values(
    by=["Run ID", "Day ID"], ascending=False
)

left_column, right_column = st.columns(2)

with left_column:
    run_option = st.selectbox(
        "Select Run:",
        runs_ids["Run ID"],
        index=None,
        placeholder="Write run ID...",
    )

    if run_option is None:
        st.write("Please select a Run ID to see the details.")
    elif run_option not in runs_ids["Run ID"].values:
        st.write("Run ID not found in the database. Please select a valid Run ID.")
    else:
        selected_row = runs_ids[runs_ids["Run ID"] == run_option].iloc[0]
        selected_run_id = selected_row["Run ID"]
        selected_day_id = selected_row["Day ID"]

        selected_run_df = runs_df[
            (runs_df["Run ID"] == selected_run_id)
            & (runs_df["Day ID"] == selected_day_id)
        ].copy()

        if selected_run_df.empty:
            st.error("Run data could not be loaded. Please try another run.")
            st.stop()

        selected_metrics_df = metrics_df[
            (metrics_df["run_id"] == selected_run_id)
            & (metrics_df["day_id"] == selected_day_id)
        ].copy()
        selected_metrics_df["metric_label"] = selected_metrics_df["metric_label"].fillna(
            selected_metrics_df["metric_id"]
        )
        # transpose the dataframe to have metrics as rows and values in a single column
        #selected_run_df = selected_run_df.melt(id_vars=['Run ID'], var_name='Metric', value_name='Value').drop(columns=['Run ID'])

        # Display run metadata as text
        container = st.container(border=True)
        container.write(f"**Run Description:** {selected_run_df['Run Description'].values[0]}")
        container.write(f"**Day ID:** {selected_run_df['Day ID'].values[0]}")
        container.write(f"**Instrument Name:** {selected_run_df['Instrument Name'].values[0]}")
        container.write(f"**Flowcell:** {selected_run_df['Flowcell Name'].values[0]}")
        container.write(f"**Reagent Kit:** {selected_run_df['Reagent Kit Name'].values[0]}")
        container.write(f"**Number of Samples:** {selected_run_df['Number of Samples'].values[0]}")
        container.write(f"**Number of Cycles:** {selected_run_df['Number of Cycles'].values[0]}")

        st.subheader("Sequencing metrics")
        if selected_metrics_df.empty:
            st.info("No sequencing metrics found for this run.")
        else:
            df_metrics = selected_metrics_df[["metric_label", "value_number", "unit"]].copy()
            df_metrics = df_metrics.rename(
                columns={"metric_label": "Metric", "value_number": "Value", "unit": "Unit"}
            )
            df_metrics["Value"] = pd.to_numeric(df_metrics["Value"], errors="coerce").round(2)
            st.dataframe(df_metrics, use_container_width=True, hide_index=True)

with right_column:
    # Filter metrics to those matching the selected run's platform
    if run_option is not None and run_option in runs_ids["Run ID"].values:
        selected_platform = selected_run_df["Platform"].values[0]
        platform_metrics = [
            col for col in metrics_columns
            if metric_platform_lookup.get(col) in (selected_platform, None)
        ]
    else:
        platform_metrics = metrics_columns

    metric_options = st.selectbox(
        "Select Metric to plot:",
        platform_metrics,
        index=None,
        placeholder="Select metric...",
    )

    if metric_options is not None and run_option is not None:
        df_same_description = runs_with_metrics[
            runs_with_metrics["Run Description"] == selected_run_df["Run Description"].values[0]
        ]
        df_same_instrument_chemistry = df_same_description[
            (df_same_description["Instrument Model"] == selected_run_df["Instrument Model"].values[0])
            & (
                df_same_description["Sequencing Chemistry ID"]
                == selected_run_df["Sequencing Chemistry ID"].values[0]
            )
        ]

        if df_same_instrument_chemistry.empty:
            st.info("No comparable runs found for this instrument model and chemistry.")
        else:
            selected_value_series = df_same_instrument_chemistry.loc[
                (df_same_instrument_chemistry["Run ID"] == selected_run_id)
                & (df_same_instrument_chemistry["Day ID"] == selected_day_id),
                metric_options,
            ]
            if selected_value_series.empty or pd.isna(selected_value_series.values[0]):
                st.info(f"No value for **{metric_options}** on this run.")
            else:
                selected_value = selected_value_series.values[0]

                st.subheader(f"Distribution plot for {metric_options}")
                metric = metric_options

                df_plot = df_same_instrument_chemistry[[metric]].copy()
                df_plot[metric] = pd.to_numeric(df_plot[metric], errors="coerce")
                df_plot = df_plot.dropna(subset=[metric])

                if len(df_plot) < 2:
                    st.info("Not enough data points to draw a density plot.")
                else:
                    # Create density plot using Altair
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

                    st.caption(
                        f"The distribution is based on {len(df_plot)} runs with the same instrument model and sequencing chemistry as the selected run."
                        f" The red line indicates the value of the selected metric for the run {selected_run_id} ({selected_day_id})."
                    )
