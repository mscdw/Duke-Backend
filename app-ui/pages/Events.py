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
limit = st.sidebar.number_input("Limit",  value=50)
event_topics = st.sidebar.selectbox("Event Topics", event_subtopics)

if 'events_df' not in st.session_state:
    st.session_state['events_df'] = None
if 'events_token' not in st.session_state:
    st.session_state['events_token'] = None

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
                st.session_state['events_df'] = None
                st.session_state['events_token'] = None
                st.info("No events found for the given parameters.")
            else:
                df = pd.DataFrame(events)
                st.session_state['events_df'] = df
                st.session_state['events_token'] = token
        except Exception as e:
            st.session_state['events_df'] = None
            st.session_state['events_token'] = None
            st.error(f"Failed to fetch events: {e}")

if st.session_state.get('events_df') is not None:
    tab1, tab2 = st.tabs(["All Events", "Media Events"])
    with tab1:
        st.dataframe(st.session_state['events_df'], height=600)
    with tab2:
        df = st.session_state['events_df']
        filtered_df = df[df['type'] == 'DEVICE_CLASSIFIED_OBJECT_MOTION_START']
        display_cols = ['thisId', 'timestamp', 'originatingEventId', 'originatingServerId', 'recordTriggerParams', 'cameraId']
        available_cols = [col for col in display_cols if col in filtered_df.columns]
        if not filtered_df.empty and available_cols:
            for idx, row in filtered_df.iterrows():
                cols = st.columns([4, 4])
                with cols[0]:
                    st.write({col: row[col] for col in available_cols})
                with cols[1]:
                    if 'cameraId' in row and 'timestamp' in row:
                        if st.button(f"Fetch Media {row['thisId']}", key=f"media_{row['thisId']}"):
                            with st.spinner("Fetching media..."):
                                try:
                                    params = {
                                        'cameraId': row['cameraId'],
                                        't': row['timestamp']
                                    }
                                    media_resp = requests.get(f"{API_URL}/media", params=params)
                                    media_resp.raise_for_status()
                                    st.video(media_resp.content)
                                except Exception as e:
                                    st.error(f"Failed to fetch media: {e}")
        else:
            st.info("No DEVICE_CLASSIFIED_OBJECT_MOTION_START events found for the selected parameters.")
    if st.session_state.get('events_token'):
        if st.button("Extend Search", key="extend_search"):
            with st.spinner("Fetching more events..."):
                try:
                    continue_params = {
                        "query_type": "CONTINUE",
                        "token": st.session_state['events_token']
                    }
                    continue_resp = requests.get(f"{API_URL}/events-search", params=continue_params)
                    continue_resp.raise_for_status()
                    continue_data = continue_resp.json()
                    more_events = continue_data['result'].get('events', [])
                    new_token = continue_data['result'].get('token')
                    if more_events:
                        df = pd.concat([st.session_state['events_df'], pd.DataFrame(more_events)], ignore_index=True)
                        if new_token and new_token != st.session_state['events_token']:
                            st.session_state['events_token'] = new_token
                        else:
                            st.session_state['events_token'] = None
                        st.session_state['events_df'] = df
                        st.rerun()
                    else:
                        st.session_state['events_token'] = None
                        st.info("No more events found.")
                except Exception as e:
                    st.error(f"Failed to fetch more events: {e}")
else:
    st.info("Fill in the parameters and click 'Search Events' to load data.")
