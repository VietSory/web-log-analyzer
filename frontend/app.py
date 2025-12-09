import streamlit as st
import pandas as pd
import requests
import time

st.set_page_config(page_title="Data Analyzer", 
                   page_icon="🛡️",
                   layout="wide",
                   initial_sidebar_state="expanded")

API_URL = "http://127.0.0.1:8000"

st.markdown("""
            <style>
                .block-container {padding-top: 1.5rem; padding-bottom: 1rem;}
                #MainMenu {visibility: hidden;}
                footer {visibility: hidden;}
            </style>
            """,unsafe_allow_html=True)
if 'current_filename' not in st.session_state:
    st.session_state["current_filename"] = None
if 'analysis_data' not in st.session_state:
    st.session_state["analysis_data"] = None
# PHẦN 1: SIDEBAR (Khu vực điều khiển)
with st.sidebar:
    st.header("Control Panel")
    st.write("---")
    st.subheader("Upload Data File")
    uploaded_file = st.file_uploader("Upload your log here ", type=["csv", "txt","log"])
    if uploaded_file is not None:
        if uploaded_file.name != st.session_state.get("last_uploaded_filename"):
            st.session_state["current_filename"] = None
        if st.button("🚀 Upload & Process", use_container_width=True):
            files = {"file": (uploaded_file.name, uploaded_file, "multipart/form-data")}
            with st.status("Đang xử lí dữ liệu,vui lòng đợi trong giây lát...",expanded=True) as status:
                try:
                    res = requests.post(f"{API_URL}/api/upload",files=files)
                    if res.status_code == 200:
                        st.session_state["current_filename"] = uploaded_file.name
                        st.session_state["last_uploaded_filename"] = uploaded_file.name
                        status.update(label = "Upload thành công!", state = "complete",expanded=False)
                        st.success(f"File ID: {uploaded_file.name}")
                    else:
                        status.update(label="Lỗi Server!", state="error")
                        st.error(res.text)
                except Exception as e:
                    status.update(label="Mất kết nối Backend!", state="error",expanded=False)
                    st.error(f"Không thể gọi API: {e}")                    
                    
    