import streamlit as st
import requests
import json

st.set_page_config(page_title="Appearance Search", layout="wide")
st.title("Avigilon Appearance Search")

API_BASE = st.secrets.get("API_BASE", "http://localhost:8000/api")

st.sidebar.header("Search Appearance")
from_time = st.sidebar.text_input("From (ISO 8601)", "2025-05-01")
to_time = st.sidebar.text_input("To (ISO 8601)", "2025-05-30")
camera_ids = st.sidebar.text_area("Camera IDs (JSON Array)", '["4xIx1DMwMLSwMDW1TDMwS9RLTsw1MBQSCK_Sf7KRwfHW3n-6ya4R3z4DAA", "4xIx1DMwMLSwMDW1TDMwS9RLTsw1MBYSCK_Sf7KRwfHW3n-6ya4R3z4DAA", "4xIx1DMwMLSwMDW1TDMwS9RLTsw1MBISCK_Sf7KRwfHW3n-6ya4R3z4DAA", "4xIx1DMwMLSwMDW1TDMwS9RLTsw1MBASCK_Sf7KRwfHW3n-6ya4R3z4DAA"]')
limit = st.sidebar.number_input("Limit", min_value=1, value=100)
scan_type = st.sidebar.selectbox("Scan Type", ["FULL", "FAST"])
appearances_type = st.sidebar.selectbox(
    "Appearances Field Type",
    ["detectedObjects", "images", "imageUrls"]
)
appearances_value = None
if appearances_type == "detectedObjects":
    source_camera_id = st.sidebar.text_input("Source Camera ID", "4xIx1DMwMLSwMDW1TDMwS9RLTsw1MBYSCK_Sf7KRwfHW3n-6ya4R3z4DAA")
    source_time = st.sidebar.text_input("Source Time (ISO 8601)", "2025-05-27T18:23:02.630Z")
    object_id = st.sidebar.number_input("Object ID", value=4680776, step=1)
    generator_id = st.sidebar.number_input("Generator ID", value=5, step=1)
    appearances_value = [
        {
            "sourceCameraId": source_camera_id,
            "sourceTime": source_time,
            "objectId": int(object_id),
            "generatorId": int(generator_id)
        }
    ]
elif appearances_type == "images":
    images = st.sidebar.text_area("Images (JSON Array)")
    try:
        appearances_value = json.loads(images)
    except Exception:
        appearances_value = []
elif appearances_type == "imageUrls":
    image_urls = st.sidebar.text_area("Image URLs (JSON Array)")
    try:
        appearances_value = json.loads(image_urls)
    except Exception:
        appearances_value = []
search = st.sidebar.button("Search")

if 'appearance_results' not in st.session_state:
    st.session_state['appearance_results'] = None
if 'appearance_token' not in st.session_state:
    st.session_state['appearance_token'] = None

if search:
    try:
        appearances = {appearances_type: appearances_value}
        payload = {
            "from": from_time,
            "to": to_time,
            "appearances": appearances,
            "cameraIds": json.loads(camera_ids),
            "limit": limit,
            "scanType": scan_type
        }
        with st.spinner("Searching appearances..."):
            resp = requests.post(f"{API_BASE}/appearance-search", json=payload)
            data = resp.json()
            results = data.get('result',{}).get('results',{})
            token = data.get('result',{}).get('token')
            if not results:
                st.session_state['appearance_results'] = None
                st.session_state['appearance_token'] = None
                st.info("No appearances found for the given parameters.")
            else:
                st.session_state['appearance_results'] = results
                st.session_state['appearance_token'] = token
    except Exception as e:
        st.error(f"Error: {e}")

if st.session_state.get('appearance_results') is not None:
    st.subheader("Search Results")
    st.json(st.session_state['appearance_results'])
    if st.session_state.get('appearance_token'):
        if st.button("Extend Search", key="extend_search"):
            with st.spinner("Fetching more appearances..."):
                try:
                    payload = {
                        "token": st.session_state['appearance_token']
                    }
                    resp = requests.post(f"{API_BASE}/appearance-search", json=payload)
                    data = resp.json()
                    more_results = data.get('result',{}).get('results',{})
                    new_token = data.get('result',{}).get('token')
                    if more_results:
                        st.session_state['appearance_results'].extend(more_results)
                        if new_token and new_token != st.session_state['appearance_token']:
                            st.session_state['appearance_token'] = new_token
                        else:
                            st.session_state['appearance_token'] = None
                        st.rerun()
                    else:
                        st.session_state['appearance_token'] = None
                        st.info("No more appearances found.")
                except Exception as e:
                    st.error(f"Error: {e}")
