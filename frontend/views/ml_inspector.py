import time

import requests
import streamlit as st

from utils import API_URL, get_display_filename


def inject_security_css():
    st.markdown("""
        <style>
            .system-status-box {
                padding: 20px; border-radius: 8px; margin-bottom: 20px;
                border: 1px solid #e0e0e0; display: flex;
                align-items: center; justify-content: space-between;
            }
            .alert-row {
                padding: 10px 0; border-bottom: 1px solid #f0f0f0;
            }
            .danger-badge {
                background-color: #dc3545; color: white;
                padding: 4px 8px; border-radius: 4px;
                font-weight: bold; font-size: 0.9em;
            }
        </style>
    """, unsafe_allow_html=True)


def render_security_monitor():
    inject_security_css()

    filename = st.session_state.get("current_filename")
    if not filename:
        st.warning("⚠️ Vui lòng upload file log trước khi quét.")
        return

    display_filename = get_display_filename(filename)
    st.title("🛡️ AI Security Monitor")
    st.markdown(f"Phát hiện bất thường cho file: **{display_filename}**")

    threats = st.session_state.get("threats_list", [])
    threat_count = len(threats)
    if threat_count == 0:
        status_props = {
            "bg": "#d4edda",
            "color": "#155724",
            "border": "#c3e6cb",
            "icon": "✅",
            "title": "Hệ thống An toàn",
            "desc": "Không phát hiện dấu hiệu tấn công.",
        }
    else:
        status_props = {
            "bg": "#f8d7da",
            "color": "#721c24",
            "border": "#f5c6cb",
            "icon": "🚨",
            "title": f"CẢNH BÁO: {threat_count} Mối đe dọa",
            "desc": "Phát hiện hành vi bất thường vượt ngưỡng an toàn.",
        }

    last_scan = st.session_state.get("last_scan_time", "Chưa quét")
    st.markdown(
        f"""
        <div class="system-status-box" style="background-color: {status_props['bg']}; color: {status_props['color']}; border-color: {status_props['border']};">
            <div>
                <h3 style="margin: 0; color: {status_props['color']};">{status_props['icon']} {status_props['title']}</h3>
                <p style="margin: 5px 0 0 0;">{status_props['desc']}</p>
            </div>
            <div style="text-align: right; font-size: 0.9em;">
                <strong>Last Scan:</strong><br>{last_scan}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("🔄 Quét ngay (AI Scan)", type="primary", use_container_width=True):
        with st.spinner("AI đang phân tích log..."):
            try:
                response = requests.post(
                    f"{API_URL}/api/scan/{filename}",
                    timeout=60,
                )
                if response.status_code == 200:
                    data = response.json()
                    st.session_state["threats_list"] = data.get("threats", [])
                    st.session_state["last_scan_time"] = time.strftime(
                        "%H:%M:%S %d/%m/%Y"
                    )
                    st.rerun()
                else:
                    st.error(f"Lỗi Server: {response.text}")
            except requests.RequestException as exc:
                st.error(f"Không thể kết nối Backend: {exc}")

    st.subheader(f"📋 Nhật ký Cảnh báo ({threat_count})")
    if not threats:
        st.info("Hệ thống sạch.")
        return

    if not st.session_state.get("stats_data"):
        try:
            stats_response = requests.get(
                f"{API_URL}/api/stats/{filename}",
                timeout=15,
            )
            if stats_response.status_code == 200:
                st.session_state["stats_data"] = stats_response.json()
        except requests.RequestException:
            pass

    if st.session_state.get("stats_data"):
        save_column, _ = st.columns([1, 3])
        with save_column:
            if st.button(
                "💾 Lưu vào Lịch sử",
                type="secondary",
                use_container_width=True,
            ):
                payload = {
                    "filename": display_filename,
                    "stats": st.session_state["stats_data"],
                    "threats": threats,
                    "owner_id": st.session_state.get("user_id"),
                }
                with st.spinner("Đang lưu báo cáo..."):
                    try:
                        response = requests.post(
                            f"{API_URL}/api/history/save",
                            json=payload,
                            timeout=15,
                        )
                        if response.status_code == 200:
                            st.success("✅ Đã lưu vào Lịch sử thành công!")
                            time.sleep(1)
                        else:
                            st.error(f"Lỗi: {response.text}")
                    except requests.RequestException as exc:
                        st.error(str(exc))

    columns = st.columns([1.5, 2, 3, 2, 1.5])
    headers = [
        "Mức độ",
        "Thời gian",
        "Chi tiết (Path)",
        "IP Nguồn",
        "Loss Score",
    ]
    for column, header in zip(columns, headers):
        column.markdown(f"**{header}**")
    st.divider()

    for threat in threats:
        severity_column, time_column, details_column, ip_column, loss_column = (
            st.columns([1.5, 2, 3, 2, 1.5])
        )
        with severity_column:
            st.markdown(
                '<span class="danger-badge">🔴 NGUY HIỂM</span>',
                unsafe_allow_html=True,
            )
        with time_column:
            st.write(threat["time"])
        with details_column:
            st.write(f"`{threat['details']}`")
        with ip_column:
            st.code(threat["ip"])
        with loss_column:
            st.write(f"**{threat['reconstruction_error']:.4f}**")
        st.markdown("<div class='alert-row'></div>", unsafe_allow_html=True)

    if st.button("Clear All Logs", type="secondary"):
        st.session_state["threats_list"] = []
        st.rerun()
