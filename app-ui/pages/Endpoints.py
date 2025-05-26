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
    ("Event Subtopics", "/event-subtopics", "GET"),
    ("Events", "/events", "GET"),
    ("Media", "/media", "POST"),
]

st.sidebar.header("API Endpoint Settings")
api_base = st.sidebar.text_input("API Base URL", API_BASE)

st.header("API Endpoints")
for name, path, method in endpoints:
    st.subheader(name)
    url = api_base + path
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
        elif path == "/events":
            server_id = st.text_input("serverId for Events", "")
            query_type = st.text_input("queryType for Events", "ACTIVE")
            params = {"serverId": server_id, "queryType": query_type} if server_id and query_type else {}
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
    elif method == "POST":
        st.write("Media POST endpoint. Provide cameraId, format, t as query params and binary body if needed.")
        camera_id = st.text_input("cameraId", "")
        format_ = st.text_input("format", "")
        t = st.text_input("t", "")
        file = st.file_uploader("Upload media body (optional)")
        params = {}
        if camera_id:
            params["cameraId"] = camera_id
        if format_:
            params["format"] = format_
        if t:
            params["t"] = t
        if st.button(f"POST {name}"):
            with st.spinner(f"Posting to {name}..."):
                try:
                    body = file.read() if file else b""
                    resp = requests.post(url, params=params, data=body)
                    st.write(f"Status: {resp.status_code}")
                    st.json(resp.json() if resp.headers.get("content-type","").startswith("application/json") else resp.text)
                except Exception as e:
                    st.error(f"Error: {e}")
