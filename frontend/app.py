import streamlit as st
import requests

Backend_URL = "http://127.0.0.1:8000"

st.title("Frontend cho Log Analyzer")
col1, col2 = st.columns(2)
with col1:
    st.info("Frontend đang chạy ngon lành!")
with col2:
    if st.button("Kiểm tra kết nối đến Backend"):
        try:
            response = requests.get(f"{Backend_URL}/api/test")
            if response.status_code == 200:
                st.success("Kết nối thành công đến Log Analyzer API!")
            else:
                st.error("Không thể kết nối đến Log Analyzer API.")
        except requests.exceptions.RequestException as e:
            st.error(f"Lỗi khi kết nối đến Log Analyzer API: {e}")