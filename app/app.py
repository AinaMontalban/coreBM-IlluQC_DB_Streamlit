import streamlit as st
import pandas as pd
import plotly.express as px
import psycopg2
from sqlalchemy import create_engine

st.set_page_config(
    page_title="IlluQC Database App",
)

st.write("# IlluQC Database App")

# Add a sidebar to choose year
st.sidebar.title("Filter by Year")

# Get list of years based on today's date
start_year = 2020
current_year = pd.Timestamp.today().year
year_list = ["All years"] + list(range(current_year, start_year - 1, -1))

# Create a selectbox for year selection
option = st.sidebar.selectbox(
    "Select Year:",
    year_list,
    index=0,
    placeholder="Select year...",
    key="selected_year",
)

selected_year = st.session_state.get("selected_year")