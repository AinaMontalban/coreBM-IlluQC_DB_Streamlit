
"""Runs page – individual run detail, metrics table, and density distribution plot."""

import streamlit as st
import pandas as pd
import altair as alt
import plotly.express as px

from db import get_engine
import queries
from constants import COLUMN_LABELS

st.set_page_config(page_title="Runs", layout="wide")

st.write("# Runs")

engine = get_engine()

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

# Fetch run metadata joined with sequencing_chemistry and instruments tables
runs_df = queries.get_runs_with_chemistry(engine)

if runs_df.empty:
    st.warning("No sequencing runs found in the database.")
    st.stop()

# Identify chemistry-attribute columns that were pivoted from the
# sequencing_chemistry_attributes long-format table. Any column not in the
# known metadata set and not in COLUMN_LABELS is assumed to be an attribute.
_meta_cols = {
    "run_id", "run_folder", "run_description", "day_id", "instrument_id",
    "platform_id", "sequencing_chemistry_id", "chemistry_name",
    "num_cycles", "num_samples",
    "instrument_model", "instrument_name",
}
chemistry_attr_cols = [
    c for c in runs_df.columns
    if c not in _meta_cols and c not in COLUMN_LABELS
]

# Fetch long-format QC metrics and map metric IDs to human-readable labels
metrics_df = queries.get_sequencing_metrics(engine)

# Rename DB column names to user-friendly labels (e.g. run_id → Run ID)
runs_df = runs_df.rename(columns=COLUMN_LABELS)

# Use DB-driven display_label directly; fall back to metric_name then metric_id
metrics_df["metric_label"] = (
    metrics_df["display_label"]
    .fillna(metrics_df["metric_name"])
    .fillna(metrics_df["metric_id"])
)

# Build lookup: metric_label → platform_id so we can later filter metrics
# to only those relevant for the selected run's sequencing platform
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

# Merge pivoted metrics into the run metadata dataframe
runs_with_metrics = runs_df.merge(
    metrics_pivot,
    left_on=["Run ID", "Day ID"],
    right_on=["run_id", "day_id"],
    how="left",
)

# Collect all available metric column names (excludes join keys)
metrics_columns = [
    col
    for col in metrics_pivot.columns
    if col not in {"run_id", "day_id"}
]

# Build the run selector list sorted by most recent first
runs_ids = runs_df[["Run ID", "Day ID"]].drop_duplicates().sort_values(
    by=["Run ID", "Day ID"], ascending=False
)

# ---------------------------------------------------------------------------
# Layout: left = run detail, right = distribution chart
# ---------------------------------------------------------------------------

left_column, right_column = st.columns(2)

with left_column:
    # --- Run selector ---
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
        # ---------------------------------------------------------------
        # Selected run data extraction
        # ---------------------------------------------------------------

        selected_row = runs_ids[runs_ids["Run ID"] == run_option].iloc[0]
        selected_run_id = selected_row["Run ID"]
        selected_day_id = selected_row["Day ID"]

        # Subset run metadata to the selected run
        selected_run_df = runs_df[
            (runs_df["Run ID"] == selected_run_id)
            & (runs_df["Day ID"] == selected_day_id)
        ].copy()

        if selected_run_df.empty:
            st.error("Run data could not be loaded. Please try another run.")
            st.stop()

        # Subset long-format QC metrics to the selected run
        selected_metrics_df = metrics_df[
            (metrics_df["run_id"] == selected_run_id)
            & (metrics_df["day_id"] == selected_day_id)
        ].copy()
        selected_metrics_df["metric_label"] = selected_metrics_df["metric_label"].fillna(
            selected_metrics_df["metric_id"]
        )

        # ---------------------------------------------------------------
        # Run detail card – metadata + chemistry info
        # ---------------------------------------------------------------

        container = st.container(border=True)
        container.write(f"**Run Description:** {selected_run_df['Run Description'].values[0]}")
        container.write(f"**Day ID:** {selected_run_df['Day ID'].values[0]}")
        container.write(f"**Instrument Name:** {selected_run_df['Instrument Name'].values[0]}")
        # Show chemistry name resolved from the sequencing_chemistry look-up table
        if "Chemistry Name" in selected_run_df.columns:
            chem_name = selected_run_df["Chemistry Name"].values[0]
            if pd.notna(chem_name) and str(chem_name).strip():
                container.write(f"**Chemistry:** {chem_name}")
        # Show any extra chemistry attributes pivoted from the long-format table
        for attr_col in chemistry_attr_cols:
            val = selected_run_df[attr_col].values[0] if attr_col in selected_run_df.columns else ""
            if pd.notna(val) and str(val).strip():
                container.write(f"**{attr_col}:** {val}")
        container.write(f"**Number of Samples:** {selected_run_df['Number of Samples'].values[0]}")
        container.write(f"**Number of Cycles:** {selected_run_df['Number of Cycles'].values[0]}")

        # ---------------------------------------------------------------
        # Sequencing metrics table
        # ---------------------------------------------------------------

        st.subheader("Sequencing metrics")
        if selected_metrics_df.empty:
            st.info("No sequencing metrics found for this run.")
        else:
            # Show a clean 3-column table: Metric / Value / Unit
            df_metrics = selected_metrics_df[["metric_label", "value_number", "unit"]].copy()
            df_metrics = df_metrics.rename(
                columns={"metric_label": "Metric", "value_number": "Value", "unit": "Unit"}
            )
            df_metrics["Value"] = pd.to_numeric(df_metrics["Value"], errors="coerce").round(2)
            st.dataframe(df_metrics, use_container_width=True, hide_index=True)

        # ---------------------------------------------------------------
        # Sample QC metrics (FastQC / MultiQC per-sample data)
        # ---------------------------------------------------------------

        st.subheader("Sample QC metrics")

        sample_metrics_df = queries.get_sample_qc_metrics_for_run(
            engine, selected_run_id
        )

        if sample_metrics_df.empty:
            st.info("No sample QC data found for this run.")
        else:
            # Use DB-driven display_label; fall back to metric_name then metric_id
            sample_metrics_df["metric_label"] = (
                sample_metrics_df["display_label"]
                .fillna(sample_metrics_df["metric_name"])
                .fillna(sample_metrics_df["metric_id"])
            )
            sample_metrics_df["value_number"] = pd.to_numeric(
                sample_metrics_df["value_number"], errors="coerce"
            )

            available_reads = sorted(
                sample_metrics_df["read"].dropna().unique().tolist()
            )
            n_samples = sample_metrics_df["sample_id"].nunique()

            # Read filter
            sample_read_filter = st.radio(
                "Read:",
                ["All"] + available_reads,
                horizontal=True,
                key="run_sample_read",
            )

            sample_table = sample_metrics_df.copy()
            if sample_read_filter != "All":
                sample_table = sample_table[
                    sample_table["read"] == sample_read_filter
                ]

            # Pivot to wide: rows = sample_id (+read), columns = metric_label
            pivot_idx = (
                ["sample_id", "read"]
                if sample_read_filter == "All"
                else ["sample_id"]
            )
            sample_wide = (
                sample_table.pivot_table(
                    index=pivot_idx,
                    columns="metric_label",
                    values="value_number",
                    aggfunc="first",
                )
                .reset_index()
            )

            st.caption(f"**{n_samples}** samples  ·  **{len(available_reads)}** reads")
            st.dataframe(
                sample_wide,
                use_container_width=True,
                hide_index=True,
                column_config={
                    col: st.column_config.NumberColumn(format="%.2f")
                    for col in sample_wide.columns
                    if col not in {"sample_id", "read"}
                },
            )

with right_column:
    # -------------------------------------------------------------------
    # Metric selector & density distribution plot
    # -------------------------------------------------------------------

    # Only show metrics relevant to the selected run's platform
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
        # -----------------------------------------------------------
        # Comparable runs – same description, instrument model, and
        # sequencing chemistry as the selected run
        # -----------------------------------------------------------

        df_same_description = runs_with_metrics[
            runs_with_metrics["Run Description"] == selected_run_df["Run Description"].values[0]
        ]
        # Further narrow to same instrument model
        mask = (
            df_same_description["Instrument Model"] == selected_run_df["Instrument Model"].values[0]
        )
        # Further narrow to same Sequencing Chemistry ID (if available)
        if "Sequencing Chemistry ID" in df_same_description.columns and "Sequencing Chemistry ID" in selected_run_df.columns:
            ref_chem = selected_run_df["Sequencing Chemistry ID"].values[0]
            if pd.notna(ref_chem):
                mask = mask & (df_same_description["Sequencing Chemistry ID"] == ref_chem)
        df_same_instrument_chemistry = df_same_description[mask]

        if df_same_instrument_chemistry.empty:
            st.info("No comparable runs found for this instrument model and chemistry.")
        else:
            # Get the selected metric value for the current run
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

                # Prepare a numeric series for the density estimation
                df_plot = df_same_instrument_chemistry[[metric]].copy()
                df_plot[metric] = pd.to_numeric(df_plot[metric], errors="coerce")
                df_plot = df_plot.dropna(subset=[metric])

                if len(df_plot) < 2:
                    st.info("Not enough data points to draw a density plot.")
                else:
                    # Altair KDE area chart showing the distribution
                    density_chart = (
                        alt.Chart(df_plot)
                        .transform_density(metric, as_=[metric, "density"])
                        .mark_area()
                        .encode(
                            x=alt.X(f"{metric}:Q", title=metric),
                            y="density:Q",
                        )
                    )

                    # Red vertical line marking the selected run's value
                    vline = (
                        alt.Chart(pd.DataFrame({metric: [selected_value]}))
                        .mark_rule(color="red", strokeWidth=2)
                        .encode(
                            x=alt.X(f"{metric}:Q"),
                            tooltip=[alt.Tooltip(f"{metric}:Q", title="Selected run")]
                        )
                    )

                    # Layer the density area and the vertical marker together
                    chart = density_chart + vline
                    st.altair_chart(chart, use_container_width=True)

                    # Explanatory caption describing the comparison cohort
                    st.caption(
                        f"The distribution is based on {len(df_plot)} runs with the same instrument model and sequencing chemistry as the selected run."
                        f" The red line indicates the value of the selected metric for the run {selected_run_id} ({selected_day_id})."
                    )
