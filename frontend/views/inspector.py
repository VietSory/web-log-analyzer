import pandas as pd
import requests
import streamlit as st

from utils import API_URL, get_display_filename


def render_inspector():
    filename = st.session_state.get("current_filename")
    display_filename = get_display_filename(filename)

    st.title("🔍 Raw Data Inspector")
    st.markdown(f"Công cụ tra cứu dữ liệu thô cho file: **{display_filename}**")

    if not filename:
        st.warning("Vui lòng upload file trước.")
        return

    if (
        "raw_logs" not in st.session_state
        or st.session_state.get("last_log_file") != filename
    ):
        with st.spinner("Đang tải dữ liệu log chi tiết..."):
            try:
                response = requests.get(
                    f"{API_URL}/api/logs/{filename}",
                    timeout=15,
                )
                if response.status_code == 200:
                    st.session_state["raw_logs"] = pd.DataFrame(response.json())
                    st.session_state["last_log_file"] = filename
                else:
                    st.error(f"Lỗi tải dữ liệu: {response.text}")
                    return
            except requests.RequestException as exc:
                st.error(f"Không thể kết nối Backend: {exc}")
                return

    dataframe = st.session_state["raw_logs"]

    if dataframe.empty:
        st.info("File log rỗng hoặc không phân tích được dữ liệu.")
        return

    with st.expander("🛠️ Bộ lọc nâng cao", expanded=True):
        ip_column, status_column = st.columns([1, 3])
        with ip_column:
            search_ip = st.text_input(
                "Tìm kiếm theo IP:",
                placeholder="VD: 192.168.1.1",
            )
        with status_column:
            available_status = sorted(dataframe["status"].unique())
            filter_status = st.multiselect(
                "Lọc theo Status Code:",
                options=available_status,
            )

    display_frame = dataframe.copy()
    if search_ip:
        display_frame = display_frame[
            display_frame["ip"].astype(str).str.contains(
                search_ip,
                case=False,
                na=False,
                regex=False,
            )
        ]

    if filter_status:
        display_frame = display_frame[
            display_frame["status"].isin(filter_status)
        ]

    st.caption(
        f"Đang hiển thị {len(display_frame)} / {len(dataframe)} dòng log."
    )

    priority_columns = ["datetime", "ip", "method", "path", "status", "size"]
    columns_to_show = [
        column for column in priority_columns if column in display_frame.columns
    ]
    columns_to_show += [
        column for column in display_frame.columns if column not in columns_to_show
    ]

    st.dataframe(
        display_frame[columns_to_show],
        use_container_width=True,
        height=600,
        column_config={
            "datetime": st.column_config.TextColumn("Time"),
            "ip": st.column_config.TextColumn("IP Address"),
            "status": st.column_config.NumberColumn("Status", format="%d"),
            "size": st.column_config.NumberColumn("Size (B)", format="%d"),
        },
    )
