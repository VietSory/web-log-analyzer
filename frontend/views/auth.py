import streamlit as st
import requests
import time
from utils import API_URL

def render_auth_page():
    col1, col2, col3 = st.columns([1, 1.5, 1]) 

    # Chỉ render nội dung vào cột giữa (col2)
    with col2:
        # Đóng khung lại cho đẹp (Container có viền)
        with st.container(border=True):
            st.markdown("<h2 style='text-align: center;'>🔐 Đăng nhập Hệ thống</h2>", unsafe_allow_html=True)
            st.write("") # Tạo khoảng cách nhỏ

            # Tạo Tab cho Login và Register
            tab1, tab2 = st.tabs(["Đăng nhập", "Đăng ký"])

            # --- TAB ĐĂNG NHẬP ---
            with tab1:
                with st.form("login_form"):
                    username = st.text_input("Tên đăng nhập")
                    password = st.text_input("Mật khẩu", type="password")
                    st.write("") # Khoảng cách nút
                    submit = st.form_submit_button("Đăng nhập", type="primary", use_container_width=True)
                    
                    if submit:
                        if not username or not password:
                            st.warning("⚠️ Vui lòng nhập đầy đủ thông tin")
                        else:
                            try:
                                res = requests.post(f"{API_URL}/api/auth/login", json={"username": username, "password": password})
                                if res.status_code == 200:
                                    st.success("✅ Đăng nhập thành công!")
                                    # Lưu trạng thái vào Session
                                    st.session_state["authenticated"] = True
                                    st.session_state["username"] = username
                                    st.session_state["user_id"] = res.json().get("user_id")
                                    time.sleep(0.5)
                                    st.rerun()
                                else:
                                    st.error(res.json().get("detail", "Đăng nhập thất bại"))
                            except Exception as e:
                                st.error(f"Lỗi kết nối: {e}")

            # --- TAB ĐĂNG KÝ ---
            with tab2:
                with st.form("register_form"):
                    new_user = st.text_input("Tên đăng nhập ")
                    fullname = st.text_input("Tên đầy đủ")
                    new_pass = st.text_input("Mật khẩu mới", type="password")
                    confirm_pass = st.text_input("Nhập lại mật khẩu", type="password")
                    st.write("")
                    reg_submit = st.form_submit_button("Đăng ký tài khoản", use_container_width=True)
                    
                    if reg_submit:
                        if new_pass != confirm_pass:
                            st.error("❌ Mật khẩu không khớp!")
                        elif not new_user or not new_pass:
                            st.warning("⚠️ Vui lòng nhập đầy đủ thông tin")
                        else:
                            try:
                                res = requests.post(
                                    f"{API_URL}/api/auth/register", 
                                    json={"username": new_user, "password": new_pass, "fullname": fullname}
                                )
                                if res.status_code == 200:
                                    st.success("✅ Đăng ký thành công! Hãy chuyển sang tab Đăng nhập.")
                                else:
                                    st.error(res.json().get("detail", "Lỗi đăng ký"))
                            except Exception as e:
                                st.error(f"Lỗi kết nối: {e}")