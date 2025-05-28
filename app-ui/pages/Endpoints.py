import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="Avigilon Endpoints", layout="wide")
st.title("Avigilon API Endpoints Explorer")

API_BASE = st.secrets.get("API_BASE", "http://localhost:8000/api")

endpoints = [
    ("Health Check", "/health", "GET"),
    ("Web Capabilities", "/wep-capabilities", "GET"),
    ("Cameras", "/cameras", "GET"),
    ("Sites", "/sites", "GET"),
    ("Site (by ID)", "/site", "GET"),
    ("Servers", "/servers", "GET"),
    ("Event Subtopics", "/event-subtopics", "GET")
]

st.header("API Endpoints")
for name, path, method in endpoints:
    st.subheader(name)
    url = API_BASE + path
    if method == "GET":
        if path == "/site":
            site_id = st.text_input(f"Site ID for {name}", "")
            params = {"id": site_id} if site_id else {}
            if st.button(f"Fetch {name}"):
                with st.spinner(f"Fetching {name}..."):
                    try:
                        resp = requests.get(url, params=params)
                        st.write(f"Status: {resp.status_code}")
                        st.json(resp.json() if resp.headers.get("content-type","").startswith("application/json") else resp.text)
                    except Exception as e:
                        st.error(f"Error: {e}")
        else:
            if st.button(f"Fetch {name}"):
                with st.spinner(f"Fetching {name}..."):
                    try:
                        resp = requests.get(url)
                        st.write(f"Status: {resp.status_code}")
                        st.json(resp.json() if resp.headers.get("content-type","").startswith("application/json") else resp.text)
                    except Exception as e:
                        st.error(f"Error: {e}")
    