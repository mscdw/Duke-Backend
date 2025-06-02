import streamlit as st
import requests
import json
import io
from PIL import Image
from collections import defaultdict
import base64

st.set_page_config(page_title="Appearance Search", layout="wide")
st.title("Avigilon Appearance Search")

API_BASE = st.secrets.get("API_BASE", "http://localhost:8000/api")

st.sidebar.header("Search Appearance")
from_time = st.sidebar.text_input("From (ISO 8601)", "2025-05-01")
to_time = st.sidebar.text_input("To (ISO 8601)", "2025-05-30")
limit = st.sidebar.number_input("Limit", min_value=1, max_value=100, value=5)
scan_type = st.sidebar.selectbox("Scan Type", ["FULL", "FAST"])
try:
    cameras_resp = requests.get(f"{API_BASE}/cameras")
    cameras = []
    if cameras_resp.ok:
        cameras_data = cameras_resp.json()
        cameras_list = cameras_data.get("result", {}).get("cameras", [])
        cameras = [(s.get("name"), s.get("id")) for s in cameras_list]
except Exception:
    cameras = []
selected_camera_ids = st.sidebar.multiselect(
    "Camera IDs",
    options=[cam[1] for cam in cameras],
    format_func=lambda x: next((name for name, id_ in cameras if id_ == x), x)
)

appearance_search_type = st.sidebar.selectbox(
    "Appearance Search Type",
    ["appearances", "querydescriptors"]
)

appearances_type = None
appearances_value = None
query_descriptors_selected = []
if appearance_search_type == "appearances":
    appearances_type = st.sidebar.selectbox(
        "Appearances Field Type",
        ["detectedObjects", "images", "imageUrls"]
    )
    if appearances_type == "detectedObjects":
        source_camera_id = st.sidebar.text_input("Source Camera ID")
        source_time = st.sidebar.text_input("Source Time (ISO 8601)")
        object_id = st.sidebar.number_input("Object ID", step=1)
        generator_id = st.sidebar.number_input("Generator ID",  step=1)
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
elif appearance_search_type == "querydescriptors":
    try:
        desc_resp = requests.get(f"{API_BASE}/appearance-descriptions")
        desc_options = []
        if desc_resp.ok:
            desc_data = desc_resp.json()
            desc_options = desc_data['result']
        else:
            desc_options = []
    except Exception:
        desc_options = []
    facet_to_tags = defaultdict(list)
    for d in desc_options:
        facet_to_tags[d['facet']].append(d['tag'])
    selected_facets = st.sidebar.multiselect("Descriptor Facets", list(facet_to_tags.keys()) if facet_to_tags else [])
    query_descriptors_selected = []
    for facet in selected_facets:
        selected_tags = st.sidebar.multiselect(
            f"Tags for {facet}",
            options=facet_to_tags[facet],
            key=f"tags_{facet}"
        )
        query_descriptors_selected.extend([{"facet": facet, "tag": tag} for tag in selected_tags])
search = st.sidebar.button("Search")

if 'appearance_results' not in st.session_state:
    st.session_state['appearance_results'] = None
if 'appearance_token' not in st.session_state:
    st.session_state['appearance_token'] = None

if search:
    try:
        if appearance_search_type == "appearances":
            appearances = {appearances_type: appearances_value}
            payload = {
                "from": from_time,
                "to": to_time,
                "appearances": appearances,
                "cameraIds": selected_camera_ids,
                "limit": limit,
                "scanType": scan_type
            }
            endpoint = f"{API_BASE}/appearance-search"
        elif appearance_search_type == "querydescriptors":
            payload = {
                "from": from_time,
                "to": to_time,
                "queryDescriptors": query_descriptors_selected,
                "cameraIds": selected_camera_ids,
                "limit": limit,
                "scanType": scan_type
            }
            endpoint = f"{API_BASE}/appearance-search-by-description"
        with st.spinner("Searching appearances..."):
            resp = requests.post(endpoint, json=payload)
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
    results = st.session_state['appearance_results']
    for idx, instance in enumerate(results):
        st.markdown(f"### Instance {idx+1}")
        st.write({k: v for k, v in instance.items() if k != 'snapshots'})
        snapshots = instance.get('snapshots', [])
        if snapshots:
            for snap_idx, snap in enumerate(snapshots):
                cols = st.columns([2, 3])
                with cols[0]:
                    st.json(snap)
                with cols[1]:
                    if st.button(f"Fetch ROI {idx}_{snap_idx}", key=f"fetch_roi_{idx}_{snap_idx}"):
                        device_gid = instance.get('deviceGid')
                        timestamp = snap.get('timestamp')
                        roi = snap.get('roi')
                        if device_gid and timestamp and roi:
                            params = {
                                'cameraId': device_gid,
                                't': timestamp,
                                'format': 'jpeg'
                            }
                            with st.spinner("Fetching and cropping image to ROI..."):
                                try:
                                    media_resp = requests.get(f"{API_BASE}/media", params=params)
                                    media_resp.raise_for_status()
                                    image = Image.open(io.BytesIO(media_resp.content))
                                    st.image(image)
                                    buffered = io.BytesIO()
                                    image.save(buffered, format="JPEG")
                                    img_b64 = base64.b64encode(buffered.getvalue()).decode()
                                    st.text_area("Base64 of Full Image", img_b64, height=150)
                                    width, height = image.size
                                    left = int(roi['left'] * width)
                                    top = int(roi['top'] * height)
                                    right = int(roi['right'] * width)
                                    bottom = int(roi['bottom'] * height)
                                    cropped = image.crop((left, top, right, bottom))
                                    st.image(cropped)
                                    buffered = io.BytesIO()
                                    cropped.save(buffered, format="JPEG")
                                    img_b64 = base64.b64encode(buffered.getvalue()).decode()
                                    st.text_area("Base64 of Cropped Image", img_b64, height=150)
                                except Exception as e:
                                    st.error(f"Failed to fetch/crop image: {e}")
                        else:
                            st.warning("Missing deviceGid, timestamp, or roi for ROI fetch.")
        else:
            st.info("No snapshots available for this instance.")

    if st.session_state.get('appearance_token'):
        if st.button("Extend Search", key="extend_search"):
            with st.spinner("Fetching more appearances..."):
                try:
                    if appearance_search_type == "appearances":
                        payload = {
                            "token": st.session_state['appearance_token']
                        }
                        endpoint = f"{API_BASE}/appearance-search"
                    elif appearance_search_type == "querydescriptors":
                        payload = {
                            "token": st.session_state['appearance_token']
                        }
                        endpoint = f"{API_BASE}/appearance-search-by-description"
                    resp = requests.post(endpoint, json=payload)
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
