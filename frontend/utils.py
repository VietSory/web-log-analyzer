import streamlit as st

API_URL = "http://127.0.0.1:8000"

def init_session_state():
    """Khởi tạo các biến toàn cục cho phiên làm việc"""
    defaults = {
        "current_filename": None,
        "last_uploaded_filename": None,
        "analysis_data": None,
        "last_scan_time": "Chưa quét",
        "threats_list": []
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def load_custom_css():
    """Inject CSS toàn cục"""
    st.markdown("""
        <style>
            /* Ẩn Header mặc định */
            header {visibility: hidden;}
            .block-container {padding-top: 2rem;}
            
            /* Style chung cho Card */
            .stCard {
                background-color: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
        </style>
    """, unsafe_allow_html=True)