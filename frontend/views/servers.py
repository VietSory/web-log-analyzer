# FILE: frontend/views/servers.py
import streamlit as st
import requests
import time
from utils import API_URL

def render_servers_page():
    st.title("🖥️ Quản lý Server")
    
    user_id = st.session_state.get("user_id")
    if not user_id:
        st.error("❌ Không tìm thấy thông tin người dùng. Vui lòng đăng nhập lại.")
        return
    
    # Section 1: Form tạo server mới
    st.subheader("➕ Thêm Server Mới")
    with st.container(border=True):
        with st.form("create_server_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                server_name = st.text_input(
                    "Tên Server *", 
                    placeholder="VD: Web Server Production",
                    help="Tên định danh cho server"
                )
            
            with col2:
                server_ipv4 = st.text_input(
                    "Địa chỉ IPv4",
                    placeholder="VD: 192.168.1.100",
                    help="Địa chỉ IP của server (tùy chọn)"
                )
            
            col_submit, col_clear = st.columns([1, 3])
            with col_submit:
                submit_btn = st.form_submit_button("🚀 Tạo Server", type="primary", use_container_width=True)
            
            if submit_btn:
                if not server_name:
                    st.error("⚠️ Vui lòng nhập tên server!")
                else:
                    with st.spinner("Đang tạo server..."):
                        try:
                            payload = {
                                "owner_id": user_id,
                                "name": server_name,
                                "ipv4": server_ipv4 if server_ipv4 else None
                            }
                            res = requests.post(f"{API_URL}/api/servers", json=payload)
                            
                            if res.status_code == 200:
                                st.success(f"✅ Đã tạo server '{server_name}' thành công!")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(f"Lỗi: {res.json().get('detail', 'Không thể tạo server')}")
                        except Exception as e:
                            st.error(f"Lỗi kết nối: {e}")
    
    st.divider()
    
    # Section 2: Danh sách server
    st.subheader("📋 Danh Sách Server của Bạn")
    
    with st.spinner("Đang tải danh sách server..."):
        try:
            res = requests.get(f"{API_URL}/api/servers/user/{user_id}")
            
            if res.status_code == 200:
                servers = res.json()
                
                if not servers:
                    st.info("📭 Bạn chưa có server nào. Hãy tạo server mới ở trên!")
                else:
                    # Hiển thị số lượng
                    st.caption(f"Tổng số: **{len(servers)}** server")
                    
                    # Hiển thị danh sách server dạng cards
                    for idx, server in enumerate(servers):
                        with st.container(border=True):
                            col_info, col_actions = st.columns([3, 1])
                            
                            with col_info:
                                st.markdown(f"### 🖥️ {server['name']}")
                                
                                # Thông tin chi tiết
                                info_col1, info_col2 = st.columns(2)
                                with info_col1:
                                    st.write(f"**ID:** `{server['id'][:16]}...`")
                                    if server.get('ipv4'):
                                        st.write(f"**IPv4:** `{server['ipv4']}`")
                                    else:
                                        st.write("**IPv4:** _Chưa cấu hình_")
                                
                                with info_col2:
                                    st.write(f"**Owner ID:** `{server['owner_id'][:16]}...`")
                            
                            with col_actions:
                                st.write("")  # Spacing
                                st.write("")
                                
                                # Nút xem chi tiết
                                if st.button(
                                    "📊 Chi tiết", 
                                    key=f"detail_server_{server['id']}", 
                                    type="primary",
                                    use_container_width=True
                                ):
                                    st.session_state["selected_server_id"] = server['id']
                                    st.session_state["current_view"] = "📊 Chi Tiết Server"
                                    st.rerun()
                                
                                # Nút xóa
                                if st.button(
                                    "🗑️ Xóa", 
                                    key=f"delete_server_{server['id']}", 
                                    type="secondary",
                                    use_container_width=True
                                ):
                                    # Confirm dialog
                                    st.session_state[f"confirm_delete_{server['id']}"] = True
                                
                                # Hiển thị confirmation
                                if st.session_state.get(f"confirm_delete_{server['id']}", False):
                                    st.warning("⚠️ Xác nhận xóa?")
                                    col_yes, col_no = st.columns(2)
                                    
                                    with col_yes:
                                        if st.button("✅ Có", key=f"confirm_yes_{server['id']}", use_container_width=True):
                                            try:
                                                del_res = requests.delete(f"{API_URL}/api/servers/{server['id']}")
                                                if del_res.status_code == 200:
                                                    st.toast(f"✅ Đã xóa server '{server['name']}'", icon="🗑️")
                                                    time.sleep(1)
                                                    st.rerun()
                                                else:
                                                    st.error("Xóa thất bại!")
                                            except Exception as e:
                                                st.error(f"Lỗi: {e}")
                                    
                                    with col_no:
                                        if st.button("❌ Không", key=f"confirm_no_{server['id']}", use_container_width=True):
                                            st.session_state[f"confirm_delete_{server['id']}"] = False
                                            st.rerun()
            else:
                st.error(f"Lỗi tải dữ liệu: {res.json().get('detail', 'Unknown error')}")
                
        except Exception as e:
            st.error(f"🔌 Không thể kết nối Backend: {e}")
