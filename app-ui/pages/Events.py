import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="Events", layout="wide")
st.title("Avigilon Server Events Dashboard")

API_URL = st.secrets.get("API_URL", "http://localhost:8000/api/events-search")

st.sidebar.header("Event Search Settings")

from_time = st.sidebar.text_input("From (ISO 8601)", "2025-01-01T19:00:00.000Z")
to_time = st.sidebar.text_input("To (ISO 8601)", "2025-05-30T19:00:00.000Z")
server_id = st.sidebar.text_input("Server ID", "V3ov5LEAQdq9_i1jRVj28w")
limit = st.sidebar.number_input("Limit", min_value=1, max_value=100, value=5)
event_topics = st.sidebar.text_input("Event Topics", "ALL")

if st.button("Search Events"):
    params = {
        "from_time": from_time,
        "to_time": to_time,
        "serverId": server_id,
        "limit": limit,
        "eventTopics": event_topics
    }
    with st.spinner("Fetching events from server..."):
        try:
            resp = requests.get(API_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
            events = data['result']['events']
            if not events:
                st.info("No events found for the given parameters.")
            else:
                df = pd.DataFrame(events)
                st.dataframe(df)
        except Exception as e:
            st.error(f"Failed to fetch events: {e}")
else:
    st.info("Fill in the parameters and click 'Search Events' to load data.")
