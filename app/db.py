"""Shared database engine for the Streamlit app."""

import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError


@st.cache_resource
def get_engine():
    """Return a cached SQLAlchemy engine built from Streamlit secrets.

    If the connection cannot be established the app shows a friendly error
    message and stops execution.
    """
    try:
        db = st.secrets["postgres"]
    except KeyError:
        st.error(
            "🔑 **Database credentials not found.**  "
            "Make sure `.streamlit/secrets.toml` contains a `[postgres]` section "
            "with `host`, `port`, `dbname`, `user`, and `password`."
        )
        st.stop()

    url = (
        f"postgresql+psycopg2://{db['user']}:{db['password']}"
        f"@{db['host']}:{db['port']}/{db['dbname']}"
    )

    engine = create_engine(url)

    # Verify the connection is reachable
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except OperationalError as exc:
        st.error(
            f"🗄️ **Cannot connect to the database.**  \n"
            f"`{db['host']}:{db['port']}/{db['dbname']}` — {exc}"
        )
        st.stop()

    return engine
