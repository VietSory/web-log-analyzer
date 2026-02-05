import time

import pandas as pd
import requests
import streamlit as st

from utils import api_request, load_custom_css


def render_history():
    load_custom_css()
    st.title("📜 Thư viện Báo cáo")

    try:
        response = api_request("GET", "/api/history/list")
    except requests.RequestException as exc:
        st.error(f"🔌 Mất kết nối tới Backend: {exc}")
        return

    if response.status_code != 200:
        st.error(f"Không thể tải lịch sử: {response.text}")
        return
    history_data = response.json()

    with st.sidebar:
        st.divider()
        st.header("⚠️ Quản lý Dữ liệu")
        with st.expander("🧨 Xóa lịch sử của tôi", expanded=False):
            st.warning("Hành động này chỉ xóa toàn bộ lịch sử quét của tài khoản hiện tại.")
            if st.button("Xác nhận xóa", type="primary", use_container_width=True):
                try:
                    delete_response = api_request("DELETE", "/api/history/clear-all")
                except requests.RequestException as exc:
                    st.error(f"Lỗi kết nối: {exc}")
                else:
                    if delete_response.status_code == 200:
                        deleted = delete_response.json().get("deleted", 0)
                        st.toast(f"✅ Đã xóa {deleted} báo cáo", icon="🗑️")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error(f"Lỗi Server: {delete_response.text}")

    if not history_data:
        st.info("📭 Chưa có lịch sử quét nào.")
        return

    dataframe = pd.DataFrame(history_data)
    dataframe["display_label"] = dataframe.apply(
        lambda row: f"{row['filename']} | {row['scan_date']} | ID: {row['id'][:8]}...",
        axis=1,
    )

    c_search, c_stats = st.columns([3, 1])
    with c_search:
        search_query = st.text_input(
            "🔍 Tìm kiếm báo cáo:",
            placeholder="Nhập tên file, ngày hoặc ID...",
        )
    with c_stats:
        st.metric("Tổng báo cáo", len(dataframe), label_visibility="visible")

    if search_query:
        query = search_query.strip()
        filtered = dataframe[
            dataframe["filename"].str.contains(query, case=False, regex=False, na=False)
            | dataframe["scan_date"].str.contains(query, case=False, regex=False, na=False)
            | dataframe["id"].astype(str).str.contains(query, case=False, regex=False, na=False)
        ]
    else:
        filtered = dataframe

    with st.container(border=True):
        st.subheader(f"🗂️ Danh sách ({len(filtered)} kết quả)")
        st.dataframe(
            filtered,
            column_config={
                "id": st.column_config.TextColumn("ID", width="medium"),
                "filename": st.column_config.TextColumn("Tên File", width="medium"),
                "scan_date": st.column_config.TextColumn("Thời gian lưu", width="medium"),
                "total_requests": st.column_config.NumberColumn("Reqs"),
                "error_rate": st.column_config.NumberColumn("Lỗi %", format="%.2f%%"),
                "display_label": None,
            },
            use_container_width=True,
            hide_index=True,
            height=300,
        )

    if filtered.empty:
        st.warning("⚠️ Không tìm thấy báo cáo nào khớp với từ khóa.")
        return

    c_select, c_btn_view, c_btn_del = st.columns([3, 1, 1], gap="small")
    with c_select:
        selected_label = st.selectbox(
            "Chọn báo cáo để thao tác:",
            filtered["display_label"],
            index=0,
            label_visibility="collapsed",
        )
        selected_id = filtered[filtered["display_label"] == selected_label]["id"].iloc[0]

    with c_btn_view:
        btn_view = st.button("📂 Xem Chi tiết", type="primary", use_container_width=True)

    with c_btn_del:
        if st.button("🗑️ Xóa", type="secondary", use_container_width=True):
            try:
                delete_response = api_request("DELETE", f"/api/history/{selected_id}")
            except requests.RequestException as exc:
                st.error(f"Lỗi: {exc}")
            else:
                if delete_response.status_code == 200:
                    st.toast("✅ Đã xóa báo cáo", icon="🗑️")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("Xóa thất bại.")

    if btn_view:
        with st.spinner("Đang tải dữ liệu báo cáo..."):
            try:
                detail_response = api_request(
                    "GET",
                    f"/api/history/detail/{selected_id}",
                )
            except requests.RequestException as exc:
                st.error(f"Lỗi kết nối: {exc}")
            else:
                if detail_response.status_code == 200:
                    render_report_detail(detail_response.json())
                else:
                    st.error("⚠️ Không tìm thấy dữ liệu báo cáo này.")


def render_report_detail(detail: dict):
    st.divider()
    st.markdown(f"### 📊 Báo cáo chi tiết: `{detail['filename']}`")
    st.caption(f"🕒 Thời gian lưu: {detail['scan_date']}")

    k1, k2, k3 = st.columns(3)
    k1.metric("Tổng Requests", f"{detail['total_requests']:,}", border=True)
    k2.metric("IP Duy nhất", f"{detail['unique_ips']:,}", border=True)
    error_rate = detail["error_rate"]
    k3.metric(
        "Tỷ lệ Lỗi (5xx)",
        f"{error_rate}%",
        delta_color="inverse" if error_rate > 5 else "normal",
        border=True,
    )

    c1, c2 = st.columns([2, 1])
    with c1:
        st.markdown("**📈 Lưu lượng theo giờ**")
        traffic = detail.get("traffic_data", {})
        if traffic:
            traffic_frame = pd.DataFrame(list(traffic.items()), columns=["Time", "Requests"])
            traffic_frame["Time"] = pd.to_datetime(traffic_frame["Time"])
            st.line_chart(traffic_frame.set_index("Time").sort_index(), height=200)
        else:
            st.info("Không có dữ liệu biểu đồ.")

    with c2:
        st.markdown("**🍩 Mã trạng thái**")
        statuses = detail.get("status_data", {})
        if statuses:
            status_frame = pd.DataFrame(list(statuses.items()), columns=["Code", "Count"])
            st.bar_chart(status_frame.set_index("Code"), height=200)

    st.subheader("🚨 Nhật ký Mối đe dọa")
    threats = detail.get("threats", [])
    if not threats:
        st.success("✅ Báo cáo này không chứa sự kiện bất thường đã lưu.")
        return

    with st.container(border=True):
        st.error(f"Phát hiện {len(threats)} hành vi bất thường.")
        threat_frame = pd.DataFrame(threats)
        columns = [
            column
            for column in ["time", "ip", "severity", "reconstruction_error", "details"]
            if column in threat_frame.columns
        ]
        st.dataframe(threat_frame[columns], use_container_width=True, hide_index=True)
