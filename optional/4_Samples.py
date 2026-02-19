import streamlit as st
import pandas as pd
import altair as alt
import plotly.express as px

st.set_page_config(page_title="Samples", layout="wide")

st.write("# Samples")

# Create the SQL connection to illuqc_db as specified in your secrets file.
conn = st.connection('illuqc_db', type='sql')

# query all runs from the database
samples_df = conn.query("SELECT * FROM sample_bioinfo_analyses_qc")

left_column, right_column = st.columns(2)

# sample ids
samples_ids = samples_df[['sample_id']].drop_duplicates().sort_values(by='sample_id', ascending=True)

# Or even better, call Streamlit functions inside a "with" block:
with left_column:
    
    selected_sample = st.selectbox(
        "Select Sample ID:",
        samples_ids,
        index=None,
        placeholder="Write Sample ID...",
    )

    # Query and display the data you inserted
    if selected_sample is None:
        st.write("Please select a Sample ID to see the details.")
    elif selected_sample not in samples_ids['sample_id'].values:
        st.write("Sample ID not found in the database. Please select a valid Sample ID.")
    else:
        selected_sample_df = conn.query(
            """
            SELECT *
            FROM sample_bioinfo_analyses_qc
            WHERE sample_id = :sample_id
            """,
            params={
                "sample_id": selected_sample,
            },
        )
        # change column names in the database query
        #selected_sample_df = selected_sample_df.rename(columns=columns_names_dict)
        # Transpose dataframe for better readability
        selected_sample_df = selected_sample_df.T
        st.table(selected_sample_df.rename(columns={0: "Value"}))

