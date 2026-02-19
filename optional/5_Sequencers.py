import streamlit as st
import pandas as pd
import altair as alt
from sqlalchemy import create_engine
import plotly.express as px

st.set_page_config(page_title="NGS Sequencers", layout="wide")

st.write("# NGS Sequencers")

# Connect to PostgreSQL directly
DB_HOST = "db"
DB_PORT = "5432"
DB_NAME = "illuqcdb"
DB_USER = "postgres"
DB_PASSWORD = "postgres"
engine = create_engine(f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

# Get sequencing qc data and join with sequencing chemistry and instrument info for all runs
sequencing_qc_df = pd.read_sql_query(
            """
            SELECT * FROM sequencing_qc sqc
            JOIN sequencing_chemistry sc ON sqc.sequencing_chemistry_id = sc.sequencing_chemistry_id
            JOIN instruments inst ON sqc.instrument_id = inst.instrument_id
            JOIN runs r ON sqc.run_id = r.run_id;
            """,
            engine
        )

# Remove duplicated columns from instruments table
sequencing_qc_df = sequencing_qc_df.loc[:, ~sequencing_qc_df.columns.duplicated()]

# Select box for instrument selection
selected_instrument = st.selectbox("Select a Sequencer", sequencing_qc_df['instrument_model'].unique())

# Filter sequencing qc data based on selected instrument
filtered_sequencing_qc_df = sequencing_qc_df[sequencing_qc_df['instrument_model'] == selected_instrument]

# Select box for metric selection
metric_options = st.selectbox(
        "Select Metric to plot:",
        filtered_sequencing_qc_df.columns.difference(['run_id', 'day_id', 'instrument_id', 'flowcell_part_number', 'reagent_kit_part_number']),
        index=None,
        placeholder="Select metric...",
    )
                   
# Radio button to color by instrument model id or run description
color_by_option = st.radio(
    "Color by:",
    ('instrument_name', 'run_description')
)

st.dataframe(filtered_sequencing_qc_df.sort_values(by='day_id'), use_container_width=True)

# Loop for each different flowcell name and reagent kit name and create a line chart of the selected metric over time for each flowcell and reagent kit combination
flowcell_reagent_combinations = filtered_sequencing_qc_df.groupby(['flowcell_part_number', 'reagent_kit_part_number']).size().reset_index().rename(columns={0: 'count'})

if metric_options is not None:

    for flowcell_reagent_combination in flowcell_reagent_combinations.itertuples():
        st.write(f"Flowcell: {flowcell_reagent_combination.flowcell_part_number}, Reagent Kit: {flowcell_reagent_combination.reagent_kit_part_number}, Number of runs: {flowcell_reagent_combination.count}")
        df_plot = filtered_sequencing_qc_df[(filtered_sequencing_qc_df['flowcell_part_number'] == flowcell_reagent_combination.flowcell_part_number) & (filtered_sequencing_qc_df['reagent_kit_part_number'] == flowcell_reagent_combination.reagent_kit_part_number)]
        st.dataframe(df_plot.sort_values(by='day_id'), use_container_width=True)

        lines = alt.Chart(df_plot).mark_line().encode(
            x='day_id:T',
            y=alt.Y(f'{metric_options}:Q', title=metric_options.replace('_', ' ').title())
        )

        points = alt.Chart(df_plot).mark_point(size=60).encode(
            x='day_id:T',
            y=alt.Y(f'{metric_options}:Q'),
            color=color_by_option
        )

        st.altair_chart(lines + points, use_container_width=True)

# if metric_options:
#     for flowcell_part_number in flowcell_part_numbers:
#         st.subheader(f"Flowcell: {flowcell_part_number}")
#         flowcell_df = filtered_sequencing_qc_df[filtered_sequencing_qc_df['flowcell_part_number'] == flowcell_part_number]

#         # Create line chart 
#         lines = alt.Chart(flowcell_df).mark_line().encode(
#             x='day_id:T',
#             y=alt.Y(f'{metric_options}:Q', title=metric_options.replace('_', ' ').title())
#         )

#         points = alt.Chart(flowcell_df).mark_point(size=60).encode(
#             x='day_id:T',
#             y=alt.Y(f'{metric_options}:Q'),
#             color=color_by_option
#         )

#         st.altair_chart(lines + points, use_container_width=True)