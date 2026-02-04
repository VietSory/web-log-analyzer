import os
from typing import Any

import requests
import streamlit as st


API_URL = os.getenv("WEB_LOG_ANALYZER_API_URL", "http://127.0.0.1:8000").rstrip("/")
API_TIMEOUT_SECONDS = 15


def init_session_state():
    defaults = {
        "current_filename": None,
        "last_uploaded_filename": None,
        "analysis_data": None,
        "last_scan_time": "Chưa quét",
        "threats_list": [],
        "current_view": None,
        "uploaded_file_labels": {},
        "access_token": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def clear_auth_session() -> None:
    for key in ("authenticated", "username", "user_id", "access_token"):
        st.session_state[key] = False if key == "authenticated" else None


def api_request(method: str, path: str, **kwargs: Any) -> requests.Response:
    headers = dict(kwargs.pop("headers", {}) or {})
    token = st.session_state.get("access_token")
    if token:
        headers.setdefault("Authorization", f"Bearer {token}")

    timeout = kwargs.pop("timeout", API_TIMEOUT_SECONDS)
    response = requests.request(
        method,
        f"{API_URL}{path}",
        headers=headers,
        timeout=timeout,
        **kwargs,
    )

    if response.status_code == 401 and token:
        clear_auth_session()

    return response


def get_display_filename(storage_name: str | None) -> str:
    if not storage_name:
        return "Unknown"
    labels = st.session_state.get("uploaded_file_labels", {})
    return labels.get(storage_name, storage_name)


def load_custom_css():
    st.markdown("""
        <style>
            .main .block-container {
                padding-top: 2rem;
                padding-bottom: 2rem;
            }
            .st-emotion-cache-1r6slb0, .st-emotion-cache-16txtl3 {
                border-radius: 10px;
                border: 1px solid #333;
                background-color: #1e1e1e;
                padding: 15px;
            }
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
            .stDataFrame { border-radius: 8px; overflow: hidden; }
        </style>
    """, unsafe_allow_html=True)
