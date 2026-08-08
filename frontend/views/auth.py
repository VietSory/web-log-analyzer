import time

import requests
import streamlit as st

from utils import API_URL


_REQUEST_TIMEOUT_SECONDS = 15


def _response_detail(response: requests.Response, fallback: str) -> str:
    try:
        return response.json().get("detail", fallback)
    except ValueError:
        return fallback


def render_auth_page():
    _, center, _ = st.columns([1, 1.5, 1])

    with center:
        with st.container(border=True):
            st.markdown("<h2 style='text-align: center;'>🔐 Đăng nhập Hệ thống</h2>", unsafe_allow_html=True)
            login_tab, register_tab = st.tabs(["Đăng nhập", "Đăng ký"])

            with login_tab:
                with st.form("login_form"):
                    username = st.text_input("Tên đăng nhập")
                    password = st.text_input("Mật khẩu", type="password")
                    submit = st.form_submit_button(
                        "Đăng nhập",
                        type="primary",
                        use_container_width=True,
                    )

                if submit:
                    if not username or not password:
                        st.warning("⚠️ Vui lòng nhập đầy đủ thông tin")
                    else:
                        try:
                            response = requests.post(
                                f"{API_URL}/api/auth/login",
                                json={"username": username, "password": password},
                                timeout=_REQUEST_TIMEOUT_SECONDS,
                            )
                        except requests.RequestException as exc:
                            st.error(f"Lỗi kết nối: {exc}")
                        else:
                            if response.status_code == 200:
                                payload = response.json()
                                st.session_state["authenticated"] = True
                                st.session_state["username"] = payload["username"]
                                st.session_state["user_id"] = payload["user_id"]
                                st.session_state["access_token"] = payload["access_token"]
                                st.success("✅ Đăng nhập thành công!")
                                time.sleep(0.3)
                                st.rerun()
                            else:
                                st.error(_response_detail(response, "Đăng nhập thất bại"))

            with register_tab:
                with st.form("register_form"):
                    new_user = st.text_input("Tên đăng nhập ")
                    fullname = st.text_input("Tên đầy đủ")
                    new_pass = st.text_input("Mật khẩu mới", type="password")
                    confirm_pass = st.text_input("Nhập lại mật khẩu", type="password")
                    reg_submit = st.form_submit_button(
                        "Đăng ký tài khoản",
                        use_container_width=True,
                    )

                if reg_submit:
                    if new_pass != confirm_pass:
                        st.error("❌ Mật khẩu không khớp!")
                    elif not new_user or not new_pass:
                        st.warning("⚠️ Vui lòng nhập đầy đủ thông tin")
                    else:
                        try:
                            response = requests.post(
                                f"{API_URL}/api/auth/register",
                                json={
                                    "username": new_user,
                                    "password": new_pass,
                                    "fullname": fullname,
                                },
                                timeout=_REQUEST_TIMEOUT_SECONDS,
                            )
                        except requests.RequestException as exc:
                            st.error(f"Lỗi kết nối: {exc}")
                        else:
                            if response.status_code == 201:
                                st.success("✅ Đăng ký thành công! Hãy chuyển sang tab Đăng nhập.")
                            else:
                                st.error(_response_detail(response, "Lỗi đăng ký"))
