import streamlit as st

st.set_page_config(
    page_title="IlluQC Database App",
    page_icon="🧬",
)

st.write("# 🧬 IlluQC Database App")

st.markdown(
    """
    Welcome to **IlluQC**, a quality-control dashboard for sequencing runs 
    stored in the IlluQC PostgreSQL database.

    Use the **sidebar** on the left to navigate between pages.
    """
)

with st.expander("ℹ️ How to use this app", expanded=True):
    st.markdown(
        """
        ### Pages

        | Page | Description |
        |------|-------------|
        | **📊 Summary** | High-level activity overview. Filter by **year** and **platform** to see the number of runs, a treemap of protocols, and a bar chart of monthly activity. |
        | **🔬 Protocols** | Explore sequencing metrics **over time** for a given protocol. Select an instrument model, chemistry combination, and QC metric, then adjust the year-range slider to zoom in. |
        | **🏃 Runs** | Inspect **individual runs**. Pick a run to see its metadata and compare a chosen metric across all runs with a density plot. |
        | **🗄️ Database** | Browse raw database tables (samples, instruments, library, protocols, QC metrics, etc.) for quick look-ups. |

        ---

        ### Typical workflow

        1. Start on **Summary** to get an overview of sequencing activity.
        2. Go to **Protocols** to monitor a specific protocol's QC trends and
           spot regressions.
        3. Use **Runs** to drill into a suspicious run and compare it against
           historical data.
        4. Check **Database** if you need to look up raw records or verify
           uploaded data.

        ---

        ### Tips

        - Most pages let you **filter by platform** (Illumina / ThermoFisher)
          so metrics and instruments are scoped correctly.
        - In the **Protocols** page, choose *"All"* in the chemistry selector
          to overlay all chemistry combinations with colour-coded lines.
        - Charts are interactive — hover for tooltips, scroll to zoom, and
          drag to pan.
        - Tables can be sorted by clicking column headers and downloaded as
          CSV via the table toolbar.
        """
    )

