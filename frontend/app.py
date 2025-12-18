import streamlit as st
import requests
import time
from utils import init_session_state, load_custom_css, API_URL
from views import home, dashboard, inspector, ml_inspector, history

st.set_page_config(
    page_title="Data Analyzer",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

init_session_state()
load_custom_css()

if "uploaded_file_list" not in st.session_state:
    st.session_state["uploaded_file_list"] = []

# SIDEBAR
with st.sidebar:
    st.header("🎛️ Control Panel")
    
    # --- KHU VỰC UPLOAD (Hỗ trợ nhiều file) ---
    with st.expander("📁 Upload Log Files", expanded=True):
        uploaded_files = st.file_uploader(
            "Chọn file (hỗ trợ chọn nhiều):", 
            type=["csv", "txt", "log"], 
            accept_multiple_files=True 
        )
        
        if uploaded_files:
            if st.button(f"🚀 Xử lý {len(uploaded_files)} file", use_container_width=True):
                # Thanh tiến trình
                progress_bar = st.progress(0)
                status_text = st.empty()
                newly_uploaded = []
                
                for i, file_obj in enumerate(uploaded_files):
                    status_text.caption(f"Đang tải lên: {file_obj.name}...")
                    files = {"file": (file_obj.name, file_obj, "multipart/form-data")}
                    try:
                        res = requests.post(f"{API_URL}/api/upload", files=files)
                        if res.status_code == 200:
                            if file_obj.name not in st.session_state["uploaded_file_list"]:
                                st.session_state["uploaded_file_list"].append(file_obj.name)                        
                            newly_uploaded.append(file_obj.name)                            
                            requests.get(f"{API_URL}/api/stats/{file_obj.name}")
                    except Exception as e:
                        st.error(f"Lỗi {file_obj.name}: {e}")
                    
                    progress_bar.progress((i + 1) / len(uploaded_files))
                
                status_text.success("✅ Hoàn tất!")
                time.sleep(0.5)
                status_text.empty()
                progress_bar.empty()                
                if newly_uploaded:
                    st.session_state["current_filename"] = newly_uploaded[0]
                    s_res = requests.get(f"{API_URL}/api/stats/{newly_uploaded[0]}")
                    if s_res.status_code == 200:
                        st.session_state['stats_data'] = s_res.json()
                    st.rerun()

    st.divider()
    
    if st.session_state["uploaded_file_list"]:
        st.subheader("📂 File đang mở")        
        selected_file = st.selectbox(
            "Chọn file để phân tích:",
            st.session_state["uploaded_file_list"],
            index=st.session_state["uploaded_file_list"].index(st.session_state["current_filename"]) if st.session_state["current_filename"] in st.session_state["uploaded_file_list"] else 0
        )        
        if selected_file != st.session_state["current_filename"]:
            st.session_state["current_filename"] = selected_file            
            with st.spinner("Đang chuyển file..."):
                s_res = requests.get(f"{API_URL}/api/stats/{selected_file}")
                if s_res.status_code == 200:
                    st.session_state['stats_data'] = s_res.json()
                st.session_state['threats_list'] = [] 
                st.rerun()
                                
        menu_options = ["🏠 Home", "📊 Dashboard", "🔍 Inspector", "🛡️ AI Monitor", "📜 History"]
    else:
        st.info("Chưa có file nào. Hãy upload bên trên.")
        menu_options = ["🏠 Home", "📜 History"]
        
    selected_view = st.radio("Chức năng:", menu_options)

#  ROUTER VIEW
if selected_view == "🏠 Home":
    home.render_home_page()
elif selected_view == "📊 Dashboard":
    dashboard.render_dashboard()
elif selected_view == "🔍 Inspector":
    inspector.render_inspector()
elif selected_view == "🛡️ AI Monitor":
    ml_inspector.render_security_monitor()
elif selected_view == "📜 History":
    history.render_history()