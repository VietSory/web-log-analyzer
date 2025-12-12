import streamlit as st
import requests
from utils import init_session_state, load_custom_css , API_URL
from views import home, dashboard, inspector, ml_inspector
import time

# 1. Cấu hình trang (Phải nằm đầu tiên)
st.set_page_config(
    page_title="Data Analyzer",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Khởi tạo & CSS
init_session_state()
load_custom_css()


# 3. SIDEBAR (Điều hướng & Upload)
with st.sidebar:
    st.header("🎛️ Control Panel")
    
    # Khu vực Upload
    st.subheader("📁 Data Source")
    uploaded_file = st.file_uploader("Upload Log File", type=["csv", "txt", "log"])
    
    if uploaded_file:
        if st.button("🚀 Process File", use_container_width=True):
            # Logic Upload
            files = {"file": (uploaded_file.name, uploaded_file, "multipart/form-data")}
            with st.status("Uploading to Backend...", expanded=True) as status:
                try:
                    res = requests.post(f"{API_URL}/api/upload", files=files)
                    if res.status_code == 200:
                        st.session_state["current_filename"] = uploaded_file.name
                        status.update(label="Upload Success!", state="complete", expanded=False)
                        st.success(f"Active File: {uploaded_file.name}")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"Server Error: {res.text}")
                except Exception as e:
                    st.error(f"Connection Error: {e}")
    
    st.divider()
    # Logic: Nếu chưa có file thì chỉ cho xem Home
    if not st.session_state["current_filename"]:
        st.warning("Vui lòng upload file để mở khóa các tính năng.")
        menu_options = ["🏠 Home"]
    else:
        st.success(f"File đang mở: {st.session_state['current_filename']}")
        menu_options = ["🏠 Home", "📊 Dashboard", "🔍 Inspector", "🛡️ AI Monitor"]
        
    selected_view = st.radio("Go to:", menu_options)

# 4. ROUTER (Điều hướng hiển thị)
if selected_view == "🏠 Home":
    home.render_home_page()
    
elif selected_view == "📊 Dashboard":
    dashboard.render_dashboard()
    
elif selected_view == "🔍 Inspector":
    inspector.render_inspector()
    
elif selected_view == "🛡️ AI Monitor":
    ml_inspector.render_security_monitor()