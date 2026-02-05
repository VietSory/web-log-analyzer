import time

import requests
import streamlit as st

from utils import api_request


def render_servers_page():
    st.title("🖥️ Quản lý Server")

    st.subheader("➕ Thêm Server Mới")
    with st.container(border=True):
        with st.form("create_server_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                server_name = st.text_input(
                    "Tên Server *",
                    placeholder="VD: Web Server Production",
                    help="Tên định danh cho server",
                )
            with col2:
                server_ipv4 = st.text_input(
                    "Địa chỉ IPv4",
                    placeholder="VD: 192.168.1.100",
                    help="Địa chỉ IP của server (tùy chọn)",
                )
            submit_btn = st.form_submit_button(
                "🚀 Tạo Server",
                type="primary",
                use_container_width=True,
            )

        if submit_btn:
            if not server_name.strip():
                st.error("⚠️ Vui lòng nhập tên server!")
            else:
                with st.spinner("Đang tạo server..."):
                    try:
                        response = api_request(
                            "POST",
                            "/api/servers",
                            json={
                                "name": server_name.strip(),
                                "ipv4": server_ipv4.strip() or None,
                            },
                        )
                    except requests.RequestException as exc:
                        st.error(f"Lỗi kết nối: {exc}")
                    else:
                        if response.status_code == 201:
                            st.success(f"✅ Đã tạo server '{server_name.strip()}' thành công!")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            try:
                                detail = response.json().get("detail", "Không thể tạo server")
                            except ValueError:
                                detail = "Không thể tạo server"
                            st.error(f"Lỗi: {detail}")

    st.divider()
    st.subheader("📋 Danh Sách Server của Bạn")

    with st.spinner("Đang tải danh sách server..."):
        try:
            response = api_request("GET", "/api/servers")
        except requests.RequestException as exc:
            st.error(f"🔌 Không thể kết nối Backend: {exc}")
            return

    if response.status_code != 200:
        st.error(f"Lỗi tải dữ liệu: {response.text}")
        return

    server_list = response.json()
    if not server_list:
        st.info("📭 Bạn chưa có server nào. Hãy tạo server mới ở trên!")
        return

    st.caption(f"Tổng số: **{len(server_list)}** server")
    for server in server_list:
        with st.container(border=True):
            col_info, col_actions = st.columns([3, 1])
            with col_info:
                st.markdown(f"### 🖥️ {server['name']}")
                st.write(f"**ID:** `{server['id'][:16]}...`")
                if server.get("ipv4"):
                    st.write(f"**IPv4:** `{server['ipv4']}`")
                else:
                    st.write("**IPv4:** _Chưa cấu hình_")

            with col_actions:
                if st.button(
                    "📊 Chi tiết",
                    key=f"detail_server_{server['id']}",
                    type="primary",
                    use_container_width=True,
                ):
                    st.session_state["selected_server_id"] = server["id"]
                    st.session_state["current_view"] = "📊 Chi Tiết Server"
                    st.rerun()

                if st.button(
                    "🗑️ Xóa",
                    key=f"delete_server_{server['id']}",
                    type="secondary",
                    use_container_width=True,
                ):
                    st.session_state[f"confirm_delete_{server['id']}"] = True

                if st.session_state.get(f"confirm_delete_{server['id']}", False):
                    st.warning("⚠️ Xác nhận xóa?")
                    yes, no = st.columns(2)
                    with yes:
                        if st.button(
                            "✅ Có",
                            key=f"confirm_yes_{server['id']}",
                            use_container_width=True,
                        ):
                            try:
                                delete_response = api_request(
                                    "DELETE",
                                    f"/api/servers/{server['id']}",
                                )
                            except requests.RequestException as exc:
                                st.error(f"Lỗi: {exc}")
                            else:
                                if delete_response.status_code == 200:
                                    st.toast(f"✅ Đã xóa server '{server['name']}'", icon="🗑️")
                                    time.sleep(0.5)
                                    st.rerun()
                                else:
                                    st.error("Xóa thất bại!")
                    with no:
                        if st.button(
                            "❌ Không",
                            key=f"confirm_no_{server['id']}",
                            use_container_width=True,
                        ):
                            st.session_state[f"confirm_delete_{server['id']}"] = False
                            st.rerun()
