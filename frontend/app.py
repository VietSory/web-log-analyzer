import time

import requests
import streamlit as st

from utils import API_URL, get_display_filename, init_session_state, load_custom_css
from views import (
    auth,
    dashboard,
    history,
    home,
    inspector,
    ml_inspector,
    server_detail,
    servers,
)


st.set_page_config(
    page_title="Data Analyzer",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_session_state()
load_custom_css()

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state.get("authenticated", False):
    auth.render_auth_page()
    st.stop()

if "uploaded_file_list" not in st.session_state:
    st.session_state["uploaded_file_list"] = []

with st.sidebar:
    st.header("🎛️ Control Panel")

    st.write(f"👤 **Xin chào:** {st.session_state.get('username', 'User')}")
    if st.button("🚪 Đăng xuất", use_container_width=True, type="secondary"):
        st.session_state["authenticated"] = False
        st.session_state["username"] = None
        st.session_state["user_id"] = None
        st.rerun()

    st.divider()
    with st.expander("📁 Upload Log Files", expanded=True):
        uploaded_files = st.file_uploader(
            "Chọn file (hỗ trợ chọn nhiều):",
            type=["txt", "log"],
            accept_multiple_files=True,
        )

        if uploaded_files and st.button(
            f"🚀 Xử lý {len(uploaded_files)} file",
            use_container_width=True,
        ):
            progress_bar = st.progress(0)
            status_text = st.empty()
            newly_uploaded: list[str] = []

            for index, file_obj in enumerate(uploaded_files):
                status_text.caption(f"Đang tải lên: {file_obj.name}...")
                files = {"file": (file_obj.name, file_obj, "text/plain")}

                try:
                    response = requests.post(
                        f"{API_URL}/api/upload",
                        files=files,
                        timeout=30,
                    )
                    if response.status_code == 200:
                        payload = response.json()
                        storage_name = payload["filename"]
                        display_name = payload.get(
                            "original_filename",
                            file_obj.name,
                        )

                        if storage_name not in st.session_state["uploaded_file_list"]:
                            st.session_state["uploaded_file_list"].append(storage_name)
                        st.session_state["uploaded_file_labels"][storage_name] = display_name
                        newly_uploaded.append(storage_name)
                    else:
                        try:
                            detail = response.json().get("detail", response.text)
                        except ValueError:
                            detail = response.text
                        st.error(f"Lỗi {file_obj.name}: {detail}")
                except requests.RequestException as exc:
                    st.error(f"Không thể tải {file_obj.name}: {exc}")

                progress_bar.progress((index + 1) / len(uploaded_files))

            status_text.success("✅ Hoàn tất!")
            time.sleep(0.5)
            status_text.empty()
            progress_bar.empty()

            if newly_uploaded:
                st.session_state["current_filename"] = newly_uploaded[0]
                try:
                    stats_response = requests.get(
                        f"{API_URL}/api/stats/{newly_uploaded[0]}",
                        timeout=15,
                    )
                    if stats_response.status_code == 200:
                        st.session_state["stats_data"] = stats_response.json()
                except requests.RequestException as exc:
                    st.error(f"Không thể tải thống kê: {exc}")
                st.rerun()

    st.divider()

    if st.session_state["uploaded_file_list"]:
        st.subheader("📂 File đang mở")
        file_list = st.session_state["uploaded_file_list"]
        current_filename = st.session_state["current_filename"]
        selected_file = st.selectbox(
            "Chọn file để phân tích:",
            file_list,
            index=file_list.index(current_filename) if current_filename in file_list else 0,
            format_func=get_display_filename,
        )

        if selected_file != current_filename:
            st.session_state["current_filename"] = selected_file
            with st.spinner("Đang chuyển file..."):
                try:
                    stats_response = requests.get(
                        f"{API_URL}/api/stats/{selected_file}",
                        timeout=15,
                    )
                    if stats_response.status_code == 200:
                        st.session_state["stats_data"] = stats_response.json()
                except requests.RequestException as exc:
                    st.error(f"Không thể tải thống kê: {exc}")
                st.session_state["threats_list"] = []
                st.rerun()

        menu_options = [
            "🏠 Home",
            "📊 Dashboard",
            "🔍 Inspector",
            "🛡️ AI Monitor",
            "🖥️ Servers",
            "📜 History",
        ]
    else:
        st.info("Chưa có file nào. Hãy upload bên trên.")
        menu_options = ["🏠 Home", "🖥️ Servers", "📜 History"]

    selected_view = st.radio("Chức năng:", menu_options)

if st.session_state.get("current_view") == "📊 Chi Tiết Server":
    server_detail.render_server_detail_page()
elif selected_view == "🏠 Home":
    home.render_home_page()
elif selected_view == "📊 Dashboard":
    dashboard.render_dashboard()
elif selected_view == "🔍 Inspector":
    inspector.render_inspector()
elif selected_view == "🛡️ AI Monitor":
    ml_inspector.render_security_monitor()
elif selected_view == "🖥️ Servers":
    servers.render_servers_page()
elif selected_view == "📜 History":
    history.render_history()
