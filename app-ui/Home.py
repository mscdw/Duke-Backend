# Main entry for Avigilon UI
import streamlit as st

st.set_page_config(page_title="Avigilon UI", layout="wide")

st.title("Avigilon API & Events Dashboard")

st.markdown("""
Welcome to the Avigilon API Explorer and Events Dashboard.

- Use the sidebar to navigate between endpoint dashboards.

**Pages:**
- Endpoints: Interact with all Avigilon API endpoints.
- Events: Visualize events from all servers.
""")
