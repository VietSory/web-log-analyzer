import streamlit as st
import time
import requests
from utils import API_URL

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
            /* Style riêng cho badge nguy hiểm */
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

    st.title("🛡️ AI Security Monitor")
    st.markdown(f"Phát hiện bất thường cho file: **{filename}**")
    threats = st.session_state.get('threats_list', [])
    threat_count = len(threats)
    if threat_count == 0:
        status_props = {
            "bg": "#d4edda", "color": "#155724", "border": "#c3e6cb",
            "icon": "✅", "title": "Hệ thống An toàn",
            "desc": "Không phát hiện dấu hiệu tấn công."
        }
    else:
        status_props = {
            "bg": "#f8d7da", "color": "#721c24", "border": "#f5c6cb",
            "icon": "🚨", "title": f"CẢNH BÁO: {threat_count} Mối đe dọa",
            "desc": "Phát hiện hành vi bất thường vượt ngưỡng an toàn."
        }

    last_scan = st.session_state.get('last_scan_time', 'Chưa quét')

    st.markdown(f"""
        <div class="system-status-box" style="background-color: {status_props['bg']}; color: {status_props['color']}; border-color: {status_props['border']};">
            <div>
                <h3 style="margin: 0; color: {status_props['color']};">{status_props['icon']} {status_props['title']}</h3>
                <p style="margin: 5px 0 0 0;">{status_props['desc']}</p>
            </div>
            <div style="text-align: right; font-size: 0.9em;">
                <strong>Last Scan:</strong><br>{last_scan}
            </div>
        </div>
    """, unsafe_allow_html=True)

    if st.button("🔄 Quét ngay (AI Scan)", type="primary", use_container_width=True):
        with st.spinner("AI đang phân tích log..."):
            try:
                res = requests.post(f"{API_URL}/api/scan/{filename}")
                if res.status_code == 200:
                    data = res.json()
                    st.session_state['threats_list'] = data.get('threats', [])
                    st.session_state['last_scan_time'] = time.strftime("%H:%M:%S %d/%m/%Y")
                    st.rerun()
                else:
                    st.error(f"Lỗi Server: {res.text}")
            except Exception as e:
                st.error(f"Không thể kết nối Backend: {e}")

    st.subheader(f"📋 Nhật ký Cảnh báo ({threat_count})")
    
    if not threats:
        st.info("Hệ thống sạch.")
    else:
        if not st.session_state.get('stats_data'):
            try:
                # Gọi API lấy thống kê ngầm để có dữ liệu lưu
                s_res = requests.get(f"{API_URL}/api/stats/{filename}")
                if s_res.status_code == 200:
                    st.session_state['stats_data'] = s_res.json()
            except: pass
        if st.session_state.get('stats_data'):
            col_save, col_info = st.columns([1, 3])
            with col_save:
                if st.button("💾 Lưu vào Lịch sử", type="secondary", use_container_width=True):
                    payload = {
                        "filename": filename,
                        "stats": st.session_state['stats_data'],
                        "threats": threats
                    }
                    with st.spinner("Đang lưu báo cáo..."):
                        try:
                            res = requests.post(f"{API_URL}/api/history/save", json=payload)
                            if res.status_code == 200:
                                st.success("✅ Đã lưu vào Lịch sử thành công!")
                                time.sleep(1)
                            else:
                                st.error(f"Lỗi: {res.text}")
                        except Exception as e:
                            st.error(str(e))
                            
        cols = st.columns([1.5, 2, 3, 2, 1.5])
        headers = ["Mức độ", "Thời gian", "Chi tiết (Path)", "IP Nguồn", "Loss Score"]
        for col, h in zip(cols, headers):
            col.markdown(f"**{h}**")
        st.divider()
        
        for t in threats:
            c1, c2, c3, c4, c5 = st.columns([1.5, 2, 3, 2, 1.5])           
            with c1: 
                st.markdown('<span class="danger-badge">🔴 NGUY HIỂM</span>', unsafe_allow_html=True)
            with c2: st.write(t['time'])
            with c3: st.write(f"`{t['details']}`") 
            with c4: st.code(t['ip'])
            with c5: st.write(f"**{t['reconstruction_error']:.4f}**")
            st.markdown("<div class='alert-row'></div>", unsafe_allow_html=True)
            
        if st.button("Clear All Logs", type="secondary"):
            st.session_state['threats_list'] = []
            st.rerun()