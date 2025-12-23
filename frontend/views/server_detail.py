# FILE: frontend/views/server_detail.py
import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime
from utils import API_URL

def render_server_detail_page():
    """Render detailed server page with warning statistics and all logs - with real-time updates"""
    
    # Hide sidebar for better full-screen experience
    st.markdown("""
        <style>
            [data-testid="stSidebar"] {
                display: none;
            }
            .main .block-container {
                max-width: 100%;
                padding-left: 2rem;
                padding-right: 2rem;
            }
        </style>
    """, unsafe_allow_html=True)
    
    # Check if server_id is in session state
    if "selected_server_id" not in st.session_state or not st.session_state.get("selected_server_id"):
        st.error("❌ Không tìm thấy thông tin server. Vui lòng quay lại trang quản lý server.")
        if st.button("⬅️ Quay lại danh sách Server"):
            st.session_state["current_view"] = "🖥️ Servers"
            st.rerun()
        return
    
    server_id = st.session_state["selected_server_id"]
    
    # Initialize auto-refresh state
    if "detail_page_refresh_counter" not in st.session_state:
        st.session_state["detail_page_refresh_counter"] = 0
    
    # Back button
    col_back, col_title, col_refresh = st.columns([1, 4, 1])
    with col_back:
        if st.button("⬅️ Quay lại", use_container_width=True):
            st.session_state["current_view"] = "🖥️ Servers"
            st.session_state.pop("selected_server_id", None)
            st.rerun()
    
    with col_refresh:
        if st.button("🔄 Refresh", use_container_width=True):
            st.session_state["detail_page_refresh_counter"] += 1
            st.rerun()
    
    # Fetch server statistics with caching
    with st.spinner("Đang tải dữ liệu server..."):
        try:
            stats_res = requests.get(f"{API_URL}/api/servers/{server_id}/stats")
            
            if stats_res.status_code == 200:
                stats_data = stats_res.json()
                server_info = stats_data.get("server", {})
                
                # Header with server info
                st.title(f"🖥️ {server_info.get('name', 'Server Detail')}")
                
                # Server basic info
                with st.container(border=True):
                    info_col1, info_col2, info_col3 = st.columns(3)
                    with info_col1:
                        st.markdown("**Server ID:**")
                        st.markdown(f"<small><code>{server_id}</code></small>", unsafe_allow_html=True)
                    with info_col2:
                        ipv4 = server_info.get('ipv4', 'N/A')
                        st.metric("IPv4", ipv4 if ipv4 else "Chưa cấu hình")
                    with info_col3:
                        st.metric("Tổng số Logs", stats_data.get("total_logs", 0))
                
                st.divider()
                
                # ==================== SECTION 1: WARNING OVERVIEW ====================
                st.subheader("⚠️ Tổng Quan Logs Warning")
                
                with st.container(border=True):
                    # Key metrics for warnings - unified status
                    metric_col1, metric_col2, metric_col3 = st.columns(3)
                    
                    with metric_col1:
                        st.metric(
                            "⚠️ Warnings", 
                            stats_data.get("warning_count", 0),
                            delta=f"{stats_data.get('warning_percentage', 0)}%",
                            delta_color="inverse"
                        )
                    
                    with metric_col2:
                        st.metric(
                            "✅ Safe Logs", 
                            stats_data.get("safe_count", 0),
                            delta=f"{stats_data.get('safe_percentage', 0)}%"
                        )
                    
                    with metric_col3:
                        st.metric(
                            "📊 Total", 
                            stats_data.get("total_logs", 0)
                        )
                    
                    st.divider()
                    
                    # Status distribution chart
                    st.markdown("### 📊 Phân Bổ Theo Status")
                    
                    chart_col1, chart_col2 = st.columns([2, 1])
                    
                    with chart_col1:
                        status_dist = stats_data.get("status_distribution", {})
                        if status_dist:
                            # Create DataFrame for chart
                            df_status = pd.DataFrame([
                                {"Status": status, "Count": count} 
                                for status, count in status_dist.items()
                            ])
                            
                            # Bar chart
                            st.bar_chart(df_status.set_index("Status"))
                        else:
                            st.info("Không có dữ liệu để hiển thị")
                    
                    with chart_col2:
                        if status_dist:
                            st.markdown("**Chi tiết:**")
                            for status, count in status_dist.items():
                                percentage = (count / stats_data.get("total_logs", 1) * 100)
                                
                                # Color coding - unified status
                                if status.lower() == 'warning':
                                    icon = "⚠️"
                                elif status.lower() == 'safe':
                                    icon = "✅"
                                else:
                                    icon = "❓"
                                
                                st.markdown(f"{icon} **{status.upper()}**: {count} ({percentage:.1f}%)")
                    
                    st.divider()
                    
                    # Recent warnings
                    st.markdown("### 🔍 Warnings Gần Đây (Top 10)")
                    warning_logs = stats_data.get("warning_logs", [])
                    
                    if warning_logs:
                        for idx, log in enumerate(warning_logs, 1):
                            with st.expander(f"⚠️ Warning #{idx} - ID: {log.get('id', '')[:12]}..."):
                                st.markdown(f"**Status:** `{log.get('status', 'N/A')}`")
                                st.markdown(f"**Contents:**")
                                st.code(log.get('contents', 'No content'), language="text")
                    else:
                        st.success("✅ Không có warning nào được ghi nhận!")
                
                st.divider()
                
                # ==================== SECTION 2: ALL LOGS ====================
                st.subheader("📜 Tất Cả Logs")
                
                # Fetch all logs
                logs_res = requests.get(f"{API_URL}/api/servers/{server_id}/logs")
                
                if logs_res.status_code == 200:
                    logs_data = logs_res.json()
                    all_logs = logs_data.get("logs", [])
                    
                    with st.container(border=True):
                        # Filters
                        filter_col1, filter_col2, filter_col3 = st.columns([2, 2, 1])
                        
                        with filter_col1:
                            # Status filter - unified status
                            status_options = ["Tất cả"] + list(set([log.get('status', 'unknown') for log in all_logs]))
                            selected_status = st.selectbox("Lọc theo Status:", status_options)
                        
                        with filter_col2:
                            # Search in contents
                            search_query = st.text_input("🔍 Tìm kiếm trong nội dung:", placeholder="Nhập từ khóa...")
                        
                        with filter_col3:
                            st.metric("Tổng logs", len(all_logs))
                        
                        # Apply filters
                        filtered_logs = all_logs
                        
                        if selected_status != "Tất cả":
                            filtered_logs = [log for log in filtered_logs if log.get('status') == selected_status]
                        
                        if search_query:
                            filtered_logs = [
                                log for log in filtered_logs 
                                if search_query.lower() in log.get('contents', '').lower()
                            ]
                        
                        st.caption(f"Hiển thị **{len(filtered_logs)}** / {len(all_logs)} logs")
                        
                        st.divider()
                        
                        # Display logs
                        if filtered_logs:
                            # Pagination
                            logs_per_page = 20
                            total_pages = (len(filtered_logs) - 1) // logs_per_page + 1
                            
                            page_col1, page_col2, page_col3 = st.columns([1, 2, 1])
                            with page_col2:
                                current_page = st.number_input(
                                    "Trang:", 
                                    min_value=1, 
                                    max_value=total_pages, 
                                    value=1, 
                                    step=1
                                )
                            
                            start_idx = (current_page - 1) * logs_per_page
                            end_idx = start_idx + logs_per_page
                            page_logs = filtered_logs[start_idx:end_idx]
                            
                            # Display logs in table format
                            for idx, log in enumerate(page_logs, start=start_idx + 1):
                                status = log.get('status', 'unknown')
                                
                                # Status icon - unified status
                                if status.lower() == 'warning':
                                    status_icon = "⚠️"
                                    border_color = "#ff9800"
                                elif status.lower() == 'safe':
                                    status_icon = "✅"
                                    border_color = "#4caf50"
                                else:
                                    status_icon = "❓"
                                    border_color = "#2196f3"
                                
                                with st.expander(f"{status_icon} Log #{idx} - Status: {status.upper()}"):
                                    log_col1, log_col2 = st.columns([1, 3])
                                    
                                    with log_col1:
                                        st.markdown(f"**Log ID:**")
                                        st.code(log.get('id', 'N/A')[:16] + "...", language="text")
                                        st.markdown(f"**Status:**")
                                        st.markdown(f"`{status.upper()}`")
                                    
                                    with log_col2:
                                        st.markdown(f"**Nội dung Log:**")
                                        st.text_area(
                                            "Content", 
                                            log.get('contents', 'No content available'),
                                            height=150,
                                            key=f"log_content_{log.get('id')}",
                                            label_visibility="collapsed"
                                        )
                        else:
                            st.info("📭 Không tìm thấy log nào phù hợp với bộ lọc.")
                else:
                    st.error(f"❌ Không thể tải logs: {logs_res.json().get('detail', 'Unknown error')}")
                    
                # Auto-refresh every 5 seconds
                st.markdown("""
                    <script>
                        setTimeout(function() {
                            location.reload();
                        }, 1000);
                    </script>
                """, unsafe_allow_html=True)
                    
            else:
                st.error(f"❌ Không thể tải thông tin server: {stats_res.json().get('detail', 'Unknown error')}")
                
        except Exception as e:
            st.error(f"🔌 Lỗi kết nối: {e}")
            st.info("Vui lòng kiểm tra kết nối backend và thử lại.")
