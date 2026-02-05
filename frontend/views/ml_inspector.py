import time

import requests
import streamlit as st

from utils import api_request, get_display_filename


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

    storage_name = st.session_state.get("current_filename")
    if not storage_name:
        st.warning("⚠️ Vui lòng upload file log trước khi quét.")
        return

    display_name = get_display_filename(storage_name)
    st.title("🛡️ AI Security Monitor")
    st.markdown(f"Phát hiện bất thường cho file: **{display_name}**")

    threats = st.session_state.get("threats_list", [])
    threat_count = len(threats)
    if threat_count == 0:
        status_props = {
            "bg": "#d4edda",
            "color": "#155724",
            "border": "#c3e6cb",
            "icon": "✅",
            "title": "Hệ thống An toàn",
            "desc": "Không phát hiện dấu hiệu bất thường.",
        }
    else:
        status_props = {
            "bg": "#f8d7da",
            "color": "#721c24",
            "border": "#f5c6cb",
            "icon": "🚨",
            "title": f"CẢNH BÁO: {threat_count} sự kiện",
            "desc": "Phát hiện hành vi bất thường vượt ngưỡng mô hình.",
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
                response = api_request("POST", f"/api/scan/{storage_name}", timeout=60)
            except requests.RequestException as exc:
                st.error(f"Không thể kết nối Backend: {exc}")
            else:
                if response.status_code == 200:
                    data = response.json()
                    st.session_state["threats_list"] = data.get("threats", [])
                    st.session_state["last_scan_time"] = time.strftime("%H:%M:%S %d/%m/%Y")
                    st.rerun()
                else:
                    st.error(f"Lỗi Server: {response.text}")

    threats = st.session_state.get("threats_list", [])
    threat_count = len(threats)
    st.subheader(f"📋 Nhật ký Cảnh báo ({threat_count})")
    if not threats:
        st.info("Không có sự kiện bất thường trong lần quét hiện tại.")
        return

    if not st.session_state.get("stats_data"):
        try:
            stats_response = api_request("GET", f"/api/stats/{storage_name}")
            if stats_response.status_code == 200:
                st.session_state["stats_data"] = stats_response.json()
        except requests.RequestException as exc:
            st.warning(f"Không thể tải thống kê để lưu báo cáo: {exc}")

    if st.session_state.get("stats_data"):
        col_save, _ = st.columns([1, 3])
        with col_save:
            if st.button("💾 Lưu vào Lịch sử", type="secondary", use_container_width=True):
                payload = {
                    "filename": display_name,
                    "stats": st.session_state["stats_data"],
                    "threats": threats,
                }
                with st.spinner("Đang lưu báo cáo..."):
                    try:
                        response = api_request("POST", "/api/history/save", json=payload)
                    except requests.RequestException as exc:
                        st.error(f"Không thể lưu báo cáo: {exc}")
                    else:
                        if response.status_code == 201:
                            st.success("✅ Đã lưu vào Lịch sử thành công!")
                            time.sleep(0.5)
                        else:
                            st.error(f"Lỗi: {response.text}")

    cols = st.columns([1.5, 2, 3, 2, 1.5])
    headers = ["Mức độ", "Thời gian", "Chi tiết", "IP Nguồn", "Loss Score"]
    for column, header in zip(cols, headers):
        column.markdown(f"**{header}**")
    st.divider()

    for threat in threats:
        c1, c2, c3, c4, c5 = st.columns([1.5, 2, 3, 2, 1.5])
        with c1:
            st.markdown(
                f'<span class="danger-badge">{threat.get("severity", "unknown")}</span>',
                unsafe_allow_html=True,
            )
        with c2:
            st.write(threat.get("time", ""))
        with c3:
            st.write(f"`{threat.get('details', '')}`")
        with c4:
            st.code(str(threat.get("ip", "Unknown")))
        with c5:
            st.write(f"**{float(threat.get('reconstruction_error', 0.0)):.4f}**")
        st.markdown("<div class='alert-row'></div>", unsafe_allow_html=True)

    if st.button("Clear All Logs", type="secondary"):
        st.session_state["threats_list"] = []
        st.rerun()
