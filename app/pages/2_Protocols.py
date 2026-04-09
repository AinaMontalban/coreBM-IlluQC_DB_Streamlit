"""Protocols page – per-protocol summary, chemistry breakdown, and time-series plots."""

import streamlit as st
import pandas as pd
import altair as alt
import plotly.express as px

from db import get_engine
import queries
from constants import COLUMN_LABELS

st.set_page_config(page_title="NGS Protocols", layout="wide")

engine = get_engine()

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

# Fetch run metadata joined with chemistry info (sequencing_chemistry table)
sequencing_qc_df = queries.get_runs_with_chemistry_protocols(engine)

# Fetch long-format QC metrics and map metric IDs to human-readable labels
metrics_df = queries.get_sequencing_metrics(engine)

# Use DB-driven display_label directly; fall back to metric_name then metric_id
metrics_df["metric_label"] = (
    metrics_df["display_label"]
    .fillna(metrics_df["metric_name"])
    .fillna(metrics_df["metric_id"])
)

# Build lookup: metric_label → platform_id so we can later filter metrics
# to only those relevant for the selected protocol's sequencing platform(s)
metric_platform_lookup = (
    metrics_df[["metric_label", "metric_platform_id"]]
    .drop_duplicates("metric_label")
    .set_index("metric_label")["metric_platform_id"]
    .to_dict()
)

# Pivot metrics from long format (one row per metric) to wide format
# (one column per metric) so each run has all its metrics in a single row
metrics_pivot = (
    metrics_df.pivot_table(
        index=["run_id", "day_id"],
        columns="metric_label",
        values="value_number",
        aggfunc="first",
    )
    .reset_index()
)

# Merge pivoted metrics into the run/chemistry dataframe
sequencing_qc_df = sequencing_qc_df.merge(
    metrics_pivot,
    on=["run_id", "day_id"],
    how="left",
)

if sequencing_qc_df.empty:
    st.warning("No sequencing data found in the database.")
    st.stop()

# ---------------------------------------------------------------------------
# Protocol selector
# ---------------------------------------------------------------------------

# Let the user pick a protocol (run_description); filter all downstream data
selected_run_description = st.selectbox("Select a Protocol", sequencing_qc_df['run_description'].unique())

filtered_sequencing_qc_df = sequencing_qc_df[sequencing_qc_df['run_description'] == selected_run_description]

if filtered_sequencing_qc_df.empty:
    st.info("No runs found for the selected protocol.")
    st.stop()

# Rename DB column names to user-friendly labels (e.g. run_id → Run ID)
filtered_sequencing_qc_df = filtered_sequencing_qc_df.rename(columns=COLUMN_LABELS)

# ---------------------------------------------------------------------------
# Top row: KPI metrics | pie chart | chemistry summary table
# ---------------------------------------------------------------------------


left_column, middle_column, right_column = st.columns([3, 2, 5])

with left_column:
    # KPI cards: total unique runs and total samples for this protocol
    total_runs = filtered_sequencing_qc_df['Run ID'].nunique()
    st.metric("Total Runs Sequenced", total_runs, border=True)
    st.metric("Total Samples Sequenced", filtered_sequencing_qc_df['Number of Samples'].sum(), border=True)

with middle_column:
    # Pie chart: distribution of runs across sequencer instruments
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
    # Summary table: mean metrics grouped by chemistry configuration.
    # "Chemistry Name" comes from the sequencing_chemistry look-up table.
    st.write("Number of runs per chemistry configuration:")

    # Collect all metric columns from the pivot (excludes run_id, day_id)
    all_metrics_columns = [
        col
        for col in metrics_pivot.columns
        if col not in {"run_id", "day_id"}
    ]

    # Keep only metrics whose platform matches the protocol's platform(s)
    # (e.g. Illumina protocols only show Illumina-specific metrics)
    protocol_platforms = filtered_sequencing_qc_df["Platform"].dropna().unique().tolist()
    metrics_columns = [
        col for col in all_metrics_columns
        if metric_platform_lookup.get(col) in (*protocol_platforms, None)
    ]

    # Build aggregation dict: mean for each metric
    metrics_agg = {metric: "mean" for metric in metrics_columns if metric in filtered_sequencing_qc_df.columns}

    # Group by Chemistry Name when available; otherwise produce a single
    # summary row (avoids a pandas error when Run ID is both the group key
    # and an aggregation target)
    group_cols = ["Chemistry Name"] if "Chemistry Name" in filtered_sequencing_qc_df.columns and not filtered_sequencing_qc_df["Chemistry Name"].isna().all() else []

    if group_cols:
        # Count runs per chemistry group via "size" on Run ID
        metrics_agg["Run ID"] = "size"
        mean_metrics = (
            filtered_sequencing_qc_df.groupby(group_cols)
            .agg(metrics_agg)
            .reset_index()
            .rename(columns={"Run ID": "Number of Runs"})
        )
    else:
        # Fallback: no chemistry info available (e.g. all NULL) — single row
        mean_metrics = (
            filtered_sequencing_qc_df[list(metrics_agg.keys())]
            .agg(metrics_agg)
            .to_frame()
            .T
        )
        mean_metrics.insert(0, "Number of Runs", len(filtered_sequencing_qc_df))

    # Prefix metric column names with "Mean" for clarity
    mean_metrics = mean_metrics.rename(
        columns={
            **{metric: f"Mean {metric}" for metric in metrics_columns},
        }
    )
    st.dataframe(mean_metrics, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# Time-series chart: metric over time for a chosen instrument + chemistry
# ---------------------------------------------------------------------------

st.subheader("Explore sequencing metrics over time")

left_column, right_column = st.columns([1, 3])

with left_column:
    # Available metrics: Number of Cycles plus platform-specific QC metrics
    metrics_cols = [
        "Number of Cycles",
        "Number of Samples",
        *[metric for metric in metrics_columns if metric in filtered_sequencing_qc_df.columns],
    ]

    # --- Filter: instrument model ---
    selected_instrument_model = st.selectbox("Select an Instrument Model", filtered_sequencing_qc_df['Instrument Model'].unique())
    
    filtered_instrument_df = filtered_sequencing_qc_df[(filtered_sequencing_qc_df['Instrument Model'] == selected_instrument_model)].copy()

    # --- Derive chemistry_combination column for chart colouring ---
    # Use Chemistry Name from the look-up table when available;
    # fall back to a single "default" group otherwise
    if "Chemistry Name" in filtered_instrument_df.columns and not filtered_instrument_df["Chemistry Name"].isna().all():
        filtered_instrument_df['chemistry_combination'] = filtered_instrument_df['Chemistry Name'].fillna('Unknown')
    else:
        filtered_instrument_df['chemistry_combination'] = "default"

    # --- Filter: chemistry combination ---
    # "All" keeps every chemistry; individual values narrow to one
    chemistry_options = ["All"] + sorted(filtered_instrument_df['chemistry_combination'].unique().tolist())
    selected_chemistry = st.selectbox("Select a Chemistry Combination", chemistry_options)

    if selected_chemistry == "All":
        filtered_chemistry_df = filtered_instrument_df.copy()
    else:
        filtered_chemistry_df = filtered_instrument_df[(filtered_instrument_df['chemistry_combination'] == selected_chemistry)]
    
    # --- Filter: metric to plot ---
    metrics_options = st.selectbox(
      "Select a Metric to plot:",
        metrics_cols,
        index=None,
        placeholder="Select metric...",
    )

    # --- Filter: year range slider ---
    # Only shown when the data spans more than one calendar year
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
    # Render the time-series line + point chart using Altair
    if metrics_options:
        # Colour each chemistry combination as a separate series
        color_enc = alt.Color(
            'chemistry_combination:N',
            legend=alt.Legend(title="Chemistry"),
        )

        x_enc = alt.X('Day ID:T', title='Date')

        # Tooltip: show run ID, instrument name, date, and metric value on hover
        tooltip_enc = [
            alt.Tooltip('Run ID:N', title='Run ID'),
            alt.Tooltip('Instrument Name:N', title='Sequencer'),
            alt.Tooltip('Day ID:T', title='Date'),
            alt.Tooltip(f'{metrics_options}:Q', title=metrics_options, format='.2f'),
        ]

        # Overlay line + scatter points for visual clarity
        fig_line = alt.Chart(plot_df).mark_line().encode(
            x=x_enc,
            y=alt.Y(f'{metrics_options}:Q', title=metrics_options.replace('_', ' ').title()),
            color=color_enc,
        ) + alt.Chart(plot_df).mark_point(size=60).encode(
            x=x_enc,
            y=alt.Y(f'{metrics_options}:Q'),
            color=color_enc,
            tooltip=tooltip_enc,
        )

        st.altair_chart(fig_line, use_container_width=True)

# ---------------------------------------------------------------------------
# Correlation scatter plot: two metrics against each other
# ---------------------------------------------------------------------------

st.subheader("Correlate two metrics")

corr_left, corr_right = st.columns([1, 3])

with corr_left:
    # Re-use the same filtered instrument + chemistry dataframe and metrics list
    corr_x = st.selectbox(
        "X-axis metric:",
        metrics_cols,
        index=None,
        placeholder="Select X metric...",
        key="corr_x",
    )
    corr_y = st.selectbox(
        "Y-axis metric:",
        metrics_cols,
        index=None,
        placeholder="Select Y metric...",
        key="corr_y",
    )

with corr_right:
    if corr_x and corr_y:
        # Build a clean numeric dataframe for the two chosen metrics
        corr_df = plot_df[["Run ID", "Instrument Name", "Day ID", "chemistry_combination", corr_x, corr_y]].copy()
        corr_df[corr_x] = pd.to_numeric(corr_df[corr_x], errors="coerce")
        corr_df[corr_y] = pd.to_numeric(corr_df[corr_y], errors="coerce")
        corr_df = corr_df.dropna(subset=[corr_x, corr_y])

        if corr_df.empty:
            st.info("Not enough data points to draw a correlation plot.")
        else:
            corr_tooltip = [
                alt.Tooltip("Run ID:N", title="Run ID"),
                alt.Tooltip("Instrument Name:N", title="Sequencer"),
                alt.Tooltip("Day ID:T", title="Date"),
                alt.Tooltip(f"{corr_x}:Q", title=corr_x, format=".2f"),
                alt.Tooltip(f"{corr_y}:Q", title=corr_y, format=".2f"),
            ]

            corr_color = alt.Color(
                "chemistry_combination:N",
                legend=alt.Legend(title="Chemistry"),
            )

            # Scatter plot with regression line
            points = (
                alt.Chart(corr_df)
                .mark_circle(size=70, opacity=0.7)
                .encode(
                    x=alt.X(f"{corr_x}:Q", title=corr_x),
                    y=alt.Y(f"{corr_y}:Q", title=corr_y),
                    color=corr_color,
                    tooltip=corr_tooltip,
                )
            )

            # Linear regression trend line across all points
            regression = (
                alt.Chart(corr_df)
                .transform_regression(corr_x, corr_y)
                .mark_line(color="gray", strokeDash=[4, 4])
                .encode(
                    x=alt.X(f"{corr_x}:Q"),
                    y=alt.Y(f"{corr_y}:Q"),
                )
            )

            st.altair_chart(points + regression, use_container_width=True)

            # Show Pearson correlation coefficient
            r_value = corr_df[corr_x].corr(corr_df[corr_y])
            st.caption(
                f"Pearson r = {r_value:.3f}  ·  {len(corr_df)} data points"
            )

# st.dataframe(filtered_sequencing_qc_df.sort_values(by='day_id'), use_container_width=True)
