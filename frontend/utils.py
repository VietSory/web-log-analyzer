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
    st.markdown("""
        <style>
            /* 1. Tùy chỉnh Container chính */
            .main .block-container {
                padding-top: 2rem;
                padding-bottom: 2rem;
            }
            
            /* 2. Style cho các Card (Khung chứa thông tin) */
            .st-emotion-cache-1r6slb0, .st-emotion-cache-16txtl3 {
                border-radius: 10px;
                border: 1px solid #333;
                background-color: #1e1e1e; /* Màu nền tối nhẹ */
                padding: 15px;
            }

            /* 3. Status Banner đẹp hơn */
            .status-box {
                padding: 15px 20px;
                border-radius: 8px;
                margin-bottom: 20px;
                font-family: 'Source Sans Pro', sans-serif;
                display: flex;
                align-items: center;
                justify-content: space-between;
                box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            }
            .status-safe { background: linear-gradient(90deg, #155724 0%, #1e7e34 100%); color: white; border: 1px solid #155724; }
            .status-danger { background: linear-gradient(90deg, #721c24 0%, #a71d2a 100%); color: white; border: 1px solid #721c24; }

            /* 4. Nút bấm to và rõ hơn */
            button[kind="primary"] {
                border-radius: 8px;
                height: 3em;
                font-weight: bold;
                transition: all 0.3s ease;
            }
            button[kind="primary"]:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(255, 75, 75, 0.4);
            }

            /* 5. Header bảng */
            .stDataFrame { border-radius: 8px; overflow: hidden; }
        </style>
    """, unsafe_allow_html=True)