import pandas as pd
import requests
import streamlit as st

from utils import api_request, get_display_filename


def render_inspector():
    storage_name = st.session_state.get("current_filename")
    display_name = get_display_filename(storage_name)
    st.title("🔍 Raw Data Inspector")
    st.markdown(f"Công cụ tra cứu dữ liệu thô cho file: **{display_name}**")

    if not storage_name:
        st.warning("Vui lòng upload file trước.")
        return

    if (
        "raw_logs" not in st.session_state
        or st.session_state.get("last_log_file") != storage_name
    ):
        with st.spinner("Đang tải dữ liệu log chi tiết..."):
            try:
                response = api_request("GET", f"/api/logs/{storage_name}")
            except requests.RequestException as exc:
                st.error(f"Không thể kết nối Backend: {exc}")
                return

            if response.status_code != 200:
                st.error(f"Lỗi tải dữ liệu: {response.text}")
                return

            st.session_state["raw_logs"] = pd.DataFrame(response.json())
            st.session_state["last_log_file"] = storage_name

    dataframe = st.session_state["raw_logs"]
    if dataframe.empty:
        st.info("File log rỗng hoặc không phân tích được dữ liệu.")
        return

    with st.expander("🛠️ Bộ lọc nâng cao", expanded=True):
        c1, c2 = st.columns([1, 3])
        with c1:
            search_ip = st.text_input(
                "Tìm kiếm theo IP:",
                placeholder="VD: 192.168.1.1",
            )
        with c2:
            available_status = (
                sorted(dataframe["status"].unique())
                if "status" in dataframe.columns
                else []
            )
            filter_status = st.multiselect(
                "Lọc theo Status Code:",
                options=available_status,
            )

    display = dataframe.copy()
    if search_ip and "ip" in display.columns:
        display = display[
            display["ip"].astype(str).str.contains(
                search_ip,
                case=False,
                na=False,
                regex=False,
            )
        ]

    if filter_status and "status" in display.columns:
        display = display[display["status"].isin(filter_status)]

    st.caption(f"Đang hiển thị {len(display)} / {len(dataframe)} dòng log.")

    priority_cols = ["datetime", "ip", "method", "path", "status", "size"]
    cols_to_show = [column for column in priority_cols if column in display.columns]
    cols_to_show += [column for column in display.columns if column not in cols_to_show]

    st.dataframe(
        display[cols_to_show],
        use_container_width=True,
        height=600,
        column_config={
            "datetime": st.column_config.TextColumn("Time"),
            "ip": st.column_config.TextColumn("IP Address"),
            "status": st.column_config.NumberColumn("Status", format="%d"),
            "size": st.column_config.NumberColumn("Size (B)", format="%d"),
        },
    )
