import streamlit as st
import pandas as pd
import time

def render_dashboard():
    filename = st.session_state.get("current_filename", "Unknown")
    st.title(f"📊 Dashboard: {filename}")
    st.caption("Tổng quan hệ thống dựa trên dữ liệu log đã tải lên.")

    # Giả lập loading nhẹ để tạo cảm giác xử lý
    with st.spinner("Đang tổng hợp dữ liệu..."):
        time.sleep(0.5) 
        
        # 1. Các chỉ số KPI (Metrics)
        col1, col2 , col3, col4 = st.columns(4)
        col1.metric("Total Requests", "15,204", "+12%", border=True)
        col2.metric("Unique IPs", "342", "-5%", border=True)
        col3.metric("Avg Body Size", "24 KB", "0%", border=True)
        col4.metric("Error Rate (5xx)", "1.2%", "Normal", border=True)
        
        st.divider()
        
        # 2. Biểu đồ
        c1, c2 = st.columns([2, 1])
        
        with c1:
            st.subheader("📈 Traffic Over Time")
            # Dữ liệu giả lập (Sau này thay bằng data thật từ API)
            chart_data = pd.DataFrame({
                'Time': pd.date_range(start='1/1/2024', periods=24, freq='H'),
                'requests': [10, 20, 50, 40, 90, 120, 150, 200, 180, 100, 50, 30] * 2
            })
            st.line_chart(chart_data.set_index('Time'), color="#00FF00")
            
        with c2:
            st.subheader("🍩 Status Codes")
            status_data = pd.DataFrame({
                'Status': ['200 OK', '404 Not Found', '500 Error', '301 Redirect'],
                'Count': [12000, 2500, 300, 404]
            })
            st.bar_chart(status_data.set_index('Status'))