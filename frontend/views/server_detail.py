import pandas as pd
import requests
import streamlit as st

from utils import api_request


def render_server_detail_page():
    server_id = st.session_state.get("selected_server_id")
    if not server_id:
        st.error("❌ Không tìm thấy thông tin server. Vui lòng quay lại trang quản lý server.")
        if st.button("⬅️ Quay lại danh sách Server"):
            st.session_state["current_view"] = "🖥️ Servers"
            st.rerun()
        return

    col_back, _, col_refresh = st.columns([1, 4, 1])
    with col_back:
        if st.button("⬅️ Quay lại", use_container_width=True):
            st.session_state["current_view"] = "🖥️ Servers"
            st.session_state.pop("selected_server_id", None)
            st.rerun()
    with col_refresh:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()

    with st.spinner("Đang tải dữ liệu server..."):
        try:
            stats_response = api_request("GET", f"/api/servers/{server_id}/stats")
        except requests.RequestException as exc:
            st.error(f"🔌 Lỗi kết nối: {exc}")
            return

    if stats_response.status_code != 200:
        st.error(f"❌ Không thể tải thông tin server: {stats_response.text}")
        return

    stats_data = stats_response.json()
    server_info = stats_data.get("server", {})
    st.title(f"🖥️ {server_info.get('name', 'Server Detail')}")

    with st.container(border=True):
        info_col1, info_col2, info_col3 = st.columns(3)
        with info_col1:
            st.markdown("**Server ID:**")
            st.code(server_id, language="text")
        with info_col2:
            st.metric("IPv4", server_info.get("ipv4") or "Chưa cấu hình")
        with info_col3:
            st.metric("Tổng số Logs", stats_data.get("total_logs", 0))

    st.divider()
    st.subheader("⚠️ Tổng Quan Logs")
    metric_col1, metric_col2, metric_col3 = st.columns(3)
    metric_col1.metric(
        "⚠️ Warnings",
        stats_data.get("warning_count", 0),
        delta=f"{stats_data.get('warning_percentage', 0)}%",
        delta_color="inverse",
    )
    metric_col2.metric(
        "✅ Safe Logs",
        stats_data.get("safe_count", 0),
        delta=f"{stats_data.get('safe_percentage', 0)}%",
    )
    metric_col3.metric("📊 Total", stats_data.get("total_logs", 0))

    status_dist = stats_data.get("status_distribution", {})
    if status_dist:
        status_frame = pd.DataFrame(
            [{"Status": key, "Count": value} for key, value in status_dist.items()]
        )
        st.bar_chart(status_frame.set_index("Status"))

    warning_logs = stats_data.get("warning_logs", [])
    if warning_logs:
        st.markdown("### 🔍 Warnings Gần Đây")
        for index, log in enumerate(warning_logs, 1):
            with st.expander(f"⚠️ Warning #{index} - {log.get('id', '')[:12]}..."):
                st.code(log.get("contents", "No content"), language="text")

    st.divider()
    st.subheader("📜 Tất Cả Logs")
    try:
        logs_response = api_request("GET", f"/api/servers/{server_id}/logs")
    except requests.RequestException as exc:
        st.error(f"Không thể tải logs: {exc}")
        return

    if logs_response.status_code != 200:
        st.error(f"❌ Không thể tải logs: {logs_response.text}")
        return

    all_logs = logs_response.json().get("logs", [])
    if not all_logs:
        st.info("📭 Server chưa có log nào.")
        return

    filter_col1, filter_col2, filter_col3 = st.columns([2, 2, 1])
    with filter_col1:
        status_options = ["Tất cả"] + sorted(
            {str(log.get("status", "unknown")) for log in all_logs}
        )
        selected_status = st.selectbox("Lọc theo Status:", status_options)
    with filter_col2:
        search_query = st.text_input(
            "🔍 Tìm kiếm trong nội dung:",
            placeholder="Nhập từ khóa...",
        )
    with filter_col3:
        st.metric("Tổng logs", len(all_logs))

    filtered_logs = all_logs
    if selected_status != "Tất cả":
        filtered_logs = [
            log for log in filtered_logs if str(log.get("status")) == selected_status
        ]
    if search_query:
        query = search_query.lower()
        filtered_logs = [
            log
            for log in filtered_logs
            if query in str(log.get("contents", "")).lower()
        ]

    st.caption(f"Hiển thị **{len(filtered_logs)}** / {len(all_logs)} logs")
    for index, log in enumerate(filtered_logs[:200], 1):
        log_status = str(log.get("status", "unknown"))
        with st.expander(f"Log #{index} - Status: {log_status.upper()}"):
            st.code(str(log.get("contents", "No content available")), language="text")
