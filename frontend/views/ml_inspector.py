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
        </style>
    """, unsafe_allow_html=True)


def render_security_monitor():
    inject_security_css()

    storage_name = st.session_state.get("current_filename")
    if not storage_name:
        st.warning("⚠️ Vui lòng upload file log trước khi quét.")
        return

    display_name = get_display_filename(storage_name)
    st.title("🛡️ Security Monitor")
    st.markdown(f"Phân tích bảo mật cho file: **{display_name}**")

    findings = st.session_state.get("threats_list", [])
    finding_count = len(findings)
    if finding_count == 0:
        status_props = {
            "bg": "#d4edda",
            "color": "#155724",
            "border": "#c3e6cb",
            "icon": "✅",
            "title": "Không có finding hiện tại",
            "desc": "Lần quét gần nhất không trả về finding bảo mật.",
        }
    else:
        status_props = {
            "bg": "#f8d7da",
            "color": "#721c24",
            "border": "#f5c6cb",
            "icon": "🚨",
            "title": f"CẢNH BÁO: {finding_count} finding",
            "desc": "Rule engine và/hoặc ML anomaly detector đã tạo finding cần xem xét.",
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

    if st.button("🔄 Quét ngay", type="primary", use_container_width=True):
        with st.spinner("Đang phân tích log..."):
            try:
                response = api_request("POST", f"/api/scan/{storage_name}", timeout=60)
            except requests.RequestException as exc:
                st.error(f"Không thể kết nối Backend: {exc}")
            else:
                if response.status_code == 200:
                    data = response.json()
                    st.session_state["threats_list"] = data.get("findings", data.get("threats", []))
                    st.session_state["analysis_result"] = data
                    st.session_state["last_scan_time"] = time.strftime("%H:%M:%S %d/%m/%Y")
                    st.rerun()
                else:
                    st.error(f"Lỗi Server: {response.text}")

    findings = st.session_state.get("threats_list", [])
    analysis_result = st.session_state.get("analysis_result", {})
    finding_count = len(findings)
    st.subheader(f"📋 Findings ({finding_count})")

    if not st.session_state.get("stats_data"):
        try:
            stats_response = api_request("GET", f"/api/stats/{storage_name}")
            if stats_response.status_code == 200:
                stats_data = stats_response.json()
                if "error" not in stats_data:
                    st.session_state["stats_data"] = stats_data
        except requests.RequestException as exc:
            st.warning(f"Không thể tải thống kê để lưu báo cáo: {exc}")

    stats_data = st.session_state.get("stats_data")
    if stats_data and analysis_result:
        col_save, _ = st.columns([1, 3])
        with col_save:
            if st.button("💾 Lưu vào Lịch sử", type="secondary", use_container_width=True):
                payload = {
                    "filename": display_name,
                    "stats": stats_data,
                    "findings": analysis_result.get("findings", findings),
                    "analysis_status": analysis_result.get("analysis_status", "degraded"),
                    "ml_status": analysis_result.get("ml_status", "not_run"),
                    "risk": analysis_result.get(
                        "risk",
                        {
                            "overall_risk_score": 0,
                            "overall_risk_severity": "none",
                            "finding_count": finding_count,
                            "rule_finding_count": 0,
                            "ml_finding_count": 0,
                            "corroborated_finding_count": 0,
                        },
                    ),
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

    if not findings:
        st.info("Không có finding trong lần quét hiện tại.")
        return

    rows = []
    for finding in findings:
        rows.append(
            {
                "source": finding.get("source", "unknown"),
                "severity": finding.get("risk_severity", finding.get("severity", "unknown")),
                "risk_score": finding.get("risk_score"),
                "time": finding.get("time", ""),
                "ip": finding.get("ip", "unknown"),
                "kind": finding.get("rule_id", finding.get("type", "unknown")),
                "details": finding.get("evidence", finding.get("details", "")),
                "reconstruction_error": finding.get("reconstruction_error"),
            }
        )
    st.dataframe(rows, use_container_width=True, hide_index=True)

    if st.button("Clear current findings", type="secondary"):
        st.session_state["threats_list"] = []
        st.session_state.pop("analysis_result", None)
        st.rerun()
