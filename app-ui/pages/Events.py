import streamlit as st
import requests
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Events", layout="wide")
st.title("Avigilon Server Events Dashboard")

API_URL = st.secrets.get("API_URL", "http://localhost:8000/api")

st.sidebar.header("Event Search Settings")

servers = []
event_subtopics = []
try:
    servers_resp = requests.get(f"{API_URL}/servers")
    if servers_resp.ok:
        servers_data = servers_resp.json()
        servers_list = servers_data.get("result", {}).get("servers", [])
        servers = [(s.get("name"), s.get("id")) for s in servers_list]
except Exception:
    servers = []
try:
    topics_resp = requests.get(f"{API_URL}/event-subtopics")
    if topics_resp.ok:
        topics_data = topics_resp.json()
        event_subtopics = topics_data.get("result", [])
except Exception:
    event_subtopics = []

query_type = st.sidebar.selectbox("Query Type", ["TIME_RANGE", "ACTIVE"])
server_id = st.sidebar.selectbox("Server ID", options=[s[1] for s in servers], format_func=lambda x: next((name for name, id_ in servers if id_ == x), x))
from_date = st.sidebar.date_input("From Date", datetime(2025, 5, 1))
to_date = st.sidebar.date_input("To Date", datetime(2025, 5, 30))
from_time = datetime.combine(from_date, datetime.min.time()).isoformat() + ".000Z"
to_time = datetime.combine(to_date, datetime.min.time()).isoformat() + ".000Z"
limit = st.sidebar.number_input("Limit",  value=20)
event_topics = st.sidebar.selectbox("Event Topics", event_subtopics)

if st.button("Search Events"):
    if(query_type == "ACTIVE"):
        params = {
            "query_type": "ACTIVE",
            "serverId": server_id,
            "limit": limit
        }
    else:
        params = {
            "query_type": query_type,
            "from_time": from_time,
            "to_time": to_time,
            "serverId": server_id,
            "limit": limit,
            "eventTopics": event_topics
        }
    with st.spinner("Fetching events from server..."):
        try:
            resp = requests.get(f"{API_URL}/events-search", params=params)
            resp.raise_for_status()
            data = resp.json()
            events = data['result']['events']
            token = data['result'].get('token')
            if not events:
                st.info("No events found for the given parameters.")
            else:
                df = pd.DataFrame(events)
                st.dataframe(df, height=min(15, len(df)) * 40)
            if token:
                if st.button("Extend Search"):
                    st.info(f"Extend search with token: {token}")
        except Exception as e:
            st.error(f"Failed to fetch events: {e}")
else:
    st.info("Fill in the parameters and click 'Search Events' to load data.")
