"""Samples page – per-sample QC metrics

Visualise sample-level quality metrics for a selected sample.
When the sample appears in multiple runs, each run is shown in its own tab.
"""

import streamlit as st
import pandas as pd
import altair as alt

from db import get_engine
import queries
from constants import COLUMN_LABELS

st.set_page_config(page_title="Sample QC", layout="wide")

st.write("# Sample QC Metrics")

engine = get_engine()

# ---------------------------------------------------------------------------
# Data loading – all sample IDs that have QC data
# ---------------------------------------------------------------------------

sample_ids_df = queries.get_sample_qc_sample_ids(engine)

if sample_ids_df.empty:
    st.warning("No sample QC data found in the database.")
    st.stop()

sample_ids_sorted = sample_ids_df["sample_id"].tolist()

# ---------------------------------------------------------------------------
# Sample selector
# ---------------------------------------------------------------------------

sample_option = st.selectbox(
    "Select Sample:",
    sample_ids_sorted,
    index=None,
    placeholder="Write sample ID...",
)

if sample_option is None:
    st.info("Please select a Sample ID to see QC details.")
    st.stop()

if sample_option not in sample_ids_sorted:
    st.warning("Sample ID not found. Please select a valid Sample ID.")
    st.stop()

# ---------------------------------------------------------------------------
# Fetch all QC metrics for the selected sample (across all runs)
# ---------------------------------------------------------------------------

metrics_df = queries.get_sample_qc_metrics_for_sample(engine, sample_option)

if metrics_df.empty:
    st.info("No QC metrics found for this sample.")
    st.stop()

# Pre-compute display labels & ensure numeric values
metrics_df["metric_label"] = (
    metrics_df["display_label"]
    .fillna(metrics_df["metric_name"])
    .fillna(metrics_df["metric_id"])
)
metrics_df["value_number"] = pd.to_numeric(
    metrics_df["value_number"], errors="coerce"
)

# ---------------------------------------------------------------------------
# Identify runs this sample belongs to (sorted newest-first)
# ---------------------------------------------------------------------------

runs_for_sample = (
    metrics_df[["run_id", "day_id", "run_description",
                 "platform_id", "instrument_name", "instrument_model",
                 "library_id", "library_name", "library_type",
                 "sex", "virtual_panel"]]
    .drop_duplicates()
    .sort_values("day_id", ascending=False)
)

run_ids = runs_for_sample["run_id"].tolist()

st.caption(
    f"Sample **{sample_option}** found in **{len(run_ids)}** run(s): "
    + ", ".join(run_ids)
)


# ---------------------------------------------------------------------------
# Helper: render content for a single run
# ---------------------------------------------------------------------------

def render_run_tab(run_id, run_metrics_df, run_info):
    """Render the detail card, metrics table and chart for one run."""

    left_col, right_col = st.columns(2)

    # ---------------------------------------------------------------
    # LEFT – detail card + metrics table
    # ---------------------------------------------------------------
    with left_col:
        # --- Sample info card (sex, virtual panel) ---
        sample_card = st.container(border=True)
        sample_card.write(f"**Sample ID:** {sample_option}")

        sex = run_info.get("sex", "")
        if pd.notna(sex) and str(sex).strip():
            sample_card.write(f"**Sex:** {sex}")

        vpanel = run_info.get("virtual_panel", "")
        if pd.notna(vpanel) and str(vpanel).strip():
            sample_card.write(f"**Virtual Panel:** {vpanel}")

        # --- Run detail card ---
        container = st.container(border=True)
        container.write(f"**Run:** {run_id}  ·  {run_info.get('day_id', '–')}")
        container.write(f"**Platform:** {run_info.get('platform_id', '–')}")
        container.write(f"**Instrument:** {run_info.get('instrument_name', '–')}")

        lib_name = run_info.get("library_name", "")
        if pd.notna(lib_name) and str(lib_name).strip():
            lib_type = run_info.get("library_type", "")
            lib_display = lib_name
            if pd.notna(lib_type) and str(lib_type).strip():
                lib_display += f" ({lib_type})"
            container.write(f"**Library:** {lib_display}")

        # --- Available dimensions for this run ---
        available_metrics = sorted(
            run_metrics_df["metric_label"].dropna().unique().tolist()
        )
        available_reads = sorted(
            run_metrics_df["read"].dropna().unique().tolist()
        )

        st.caption(
            f"**{len(available_reads)}** read(s)  ·  "
            f"**{len(available_metrics)}** metrics"
        )

        # --- Metrics table (wide format) ---
        st.subheader("Metrics table")

        read_filter = st.radio(
            "Read:",
            ["All"] + available_reads,
            horizontal=True,
            key=f"table_read_{run_id}",
        )

        table_df = run_metrics_df.copy()
        if read_filter != "All":
            table_df = table_df[table_df["read"] == read_filter]

        pivot_index = ["read"] if read_filter == "All" else []

        if pivot_index:
            wide_df = (
                table_df.pivot_table(
                    index=pivot_index,
                    columns="metric_label",
                    values="value_number",
                    aggfunc="first",
                )
                .reset_index()
            )
        else:
            wide_df = (
                table_df.pivot_table(
                    columns="metric_label",
                    values="value_number",
                    aggfunc="first",
                )
                .to_frame()
                .T.reset_index(drop=True)
            )

        st.dataframe(
            wide_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                col: st.column_config.NumberColumn(format="%.2f")
                for col in wide_df.columns
                if col not in {"read"}
            },
        )

    # ---------------------------------------------------------------
    # RIGHT – density plot (library cohort) for a selected metric
    # ---------------------------------------------------------------
    with right_col:
        metric_choice = st.selectbox(
            "Select Metric to plot:",
            available_metrics,
            index=None,
            placeholder="Select metric...",
            key=f"dist_metric_{run_id}",
        )

        dist_read = st.radio(
            "Read:",
            ["All"] + available_reads,
            horizontal=True,
            key=f"dist_read_{run_id}",
        )

        if metric_choice is not None:
            # --- Determine library for this sample/run ---
            lib_id = run_info.get("library_id") if hasattr(run_info, "get") else run_info.get("library_id", None)
            lib_name = run_info.get("library_name", "")

            if pd.isna(lib_id) or not str(lib_id).strip():
                st.info("No library assigned for this sample/run — cannot show cohort distribution.")
            else:
                # Fetch all samples with the same library in this run
                cohort_df = queries.get_sample_qc_metrics_by_library(engine, str(lib_id), run_id)
                cohort_df["metric_label"] = (
                    cohort_df["display_label"]
                    .fillna(cohort_df["metric_name"])
                    .fillna(cohort_df["metric_id"])
                )
                cohort_df["value_number"] = pd.to_numeric(
                    cohort_df["value_number"], errors="coerce"
                )

                # Filter to selected metric / read
                cohort_metric = cohort_df[
                    cohort_df["metric_label"] == metric_choice
                ].copy()
                if dist_read != "All":
                    cohort_metric = cohort_metric[cohort_metric["read"] == dist_read]

                if cohort_metric.empty:
                    st.info("No cohort data for the selected metric / read combination.")
                else:
                    n_samples = cohort_metric["sample_id"].nunique()
                    lib_display = lib_name if pd.notna(lib_name) and str(lib_name).strip() else str(lib_id)
                    st.subheader(f"Distribution: {metric_choice}")
                    st.caption(
                        f"Density across **{n_samples}** samples with library "
                        f"**{lib_display}** in run **{run_id}**"
                    )

                    # Current sample's values
                    sample_vals = cohort_metric[
                        cohort_metric["sample_id"] == sample_option
                    ].copy()

                    if dist_read == "All":
                        # Faceted density – one row per read
                        density_chart = (
                            alt.Chart(cohort_metric)
                            .transform_density(
                                density="value_number",
                                as_=["value", "density"],
                                groupby=["read"],
                            )
                            .mark_area(opacity=0.35)
                            .encode(
                                x=alt.X("value:Q", title=metric_choice),
                                y=alt.Y("density:Q", title="Density"),
                                color=alt.Color("read:N", title="Read"),
                            )
                        )

                        # Vertical rule for selected sample per read
                        rule_chart = (
                            alt.Chart(sample_vals)
                            .mark_rule(strokeDash=[6, 3], strokeWidth=2)
                            .encode(
                                x=alt.X("value_number:Q"),
                                color=alt.Color("read:N"),
                                tooltip=[
                                    alt.Tooltip("read:N", title="Read"),
                                    alt.Tooltip("value_number:Q", title=metric_choice, format=".2f"),
                                ],
                            )
                        )

                        chart = (density_chart + rule_chart).properties(height=350)
                    else:
                        # Single read – simple density
                        density_chart = (
                            alt.Chart(cohort_metric)
                            .transform_density(
                                density="value_number",
                                as_=["value", "density"],
                            )
                            .mark_area(opacity=0.35, color="#4c78a8")
                            .encode(
                                x=alt.X("value:Q", title=metric_choice),
                                y=alt.Y("density:Q", title="Density"),
                            )
                        )

                        # Vertical rule for selected sample
                        rule_chart = (
                            alt.Chart(sample_vals)
                            .mark_rule(
                                color="#e45756",
                                strokeDash=[6, 3],
                                strokeWidth=2,
                            )
                            .encode(
                                x=alt.X("value_number:Q"),
                                tooltip=[
                                    alt.Tooltip(
                                        "value_number:Q",
                                        title=metric_choice,
                                        format=".2f",
                                    ),
                                ],
                            )
                        )

                        chart = (density_chart + rule_chart).properties(height=350)

                    st.altair_chart(chart, use_container_width=True)

                    # Summary statistics for the cohort
                    if dist_read == "All":
                        summary = (
                            cohort_metric.groupby("read")["value_number"]
                            .describe()
                            .round(2)
                        )
                    else:
                        summary = (
                            cohort_metric["value_number"]
                            .describe()
                            .to_frame()
                            .T.round(2)
                        )
                    st.dataframe(summary, use_container_width=True)


# ---------------------------------------------------------------------------
# Render: one tab per run (or flat layout if single run)
# ---------------------------------------------------------------------------

if len(run_ids) == 1:
    rid = run_ids[0]
    run_info = runs_for_sample[runs_for_sample["run_id"] == rid].iloc[0]
    run_data = metrics_df[metrics_df["run_id"] == rid]
    render_run_tab(rid, run_data, run_info)
else:
    tab_labels = [
        f"{row['run_id']}  ({row['day_id']})"
        for _, row in runs_for_sample.iterrows()
    ]
    tabs = st.tabs(tab_labels)

    for tab, (_, row) in zip(tabs, runs_for_sample.iterrows()):
        rid = row["run_id"]
        run_data = metrics_df[metrics_df["run_id"] == rid]
        with tab:
            render_run_tab(rid, run_data, row)
