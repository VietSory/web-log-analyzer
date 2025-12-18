import streamlit as st
import pandas as pd
import requests
from utils import API_URL

def render_dashboard():
    filename = st.session_state.get("current_filename", "Unknown")
    st.title(f"📊 Dashboard: {filename}")
    if filename == "Unknown" or not filename:
        st.warning("Vui lòng upload file trước.")
        return
    st.caption("Tổng quan hệ thống dựa trên dữ liệu log đã tải lên.")
    with st.spinner("Đang đồng bộ dữ liệu từ Server..."):
        try:
            response = requests.get(f"{API_URL}/api/stats/{filename}")
            if response.status_code == 200:
                data = response.json()
            else:
                st.error(f"Lỗi Backend: {response.text}")
                return
        except Exception as e:
            st.error(f"Không thể kết nối Backend: {e}")
            return

        # Các chỉ số KPI (Metrics)
        col1, col2 , col3, col4 = st.columns(4)
        total = data.get("total_requests", 0)
        col1.metric("Total Requests", f"{total:,}", border=True)
        unique = data.get("unique_ips", 0)
        col2.metric("Unique IPs", f"{unique:,}", border=True)
        size = data.get("avg_body_size", 0)
        col3.metric("Avg Body Size", f"{size} KB", border=True)
        err_rate = data.get("error_rate", 0)
        delta_color = "normal" if err_rate < 5 else "inverse"
        col4.metric("Error Rate (5xx)", f"{err_rate}%", delta_color=delta_color, border=True)
        st.divider()
        
        # Biểu đồ
        c1, c2 = st.columns([2, 1])
        with c1:
            st.subheader("📈 Traffic Over Time")
            traffic_data = data.get("traffic_chart", {})
            if traffic_data:
                # Chuyển đổi Dict từ API thành DataFrame cho Streamlit
                chart_df = pd.DataFrame(list(traffic_data.items()), columns=['Time', 'Requests'])
                chart_df['Time'] = pd.to_datetime(chart_df['Time'])
                chart_df = chart_df.set_index('Time')
                st.line_chart(chart_df, color="#00FF00")
            else:
                st.info("Không có dữ liệu thời gian trong file log.")
        with c2:
            st.subheader("🍩 Status Codes")
            status_dict = data.get("status_distribution", {})
            if status_dict:
                status_df = pd.DataFrame(list(status_dict.items()), columns=['Status', 'Count'])
                status_df = status_df.set_index('Status')
                st.bar_chart(status_df)
            else:
                st.info("Không có dữ liệu status code.")