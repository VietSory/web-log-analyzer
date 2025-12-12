import streamlit as st
import time

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
    
    st.title("🛡️ AI Security Monitor")
    st.markdown("Phát hiện bất thường dựa trên Deep Learning Autoencoder.")

    # 1. TRẠNG THÁI HỆ THỐNG (STATUS BANNER)
    threat_count = len(st.session_state['threats_list'])    
    
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
            "desc": "Cần hành động ngay lập tức!"
        }

    st.markdown(f"""
        <div class="system-status-box" style="background-color: {status_props['bg']}; color: {status_props['color']}; border-color: {status_props['border']};">
            <div>
                <h3 style="margin: 0; color: {status_props['color']};">{status_props['icon']} {status_props['title']}</h3>
                <p style="margin: 5px 0 0 0;">{status_props['desc']}</p>
            </div>
            <div style="text-align: right; font-size: 0.9em;">
                <strong>Last Scan:</strong><br>{st.session_state['last_scan_time']}
            </div>
        </div>
    """, unsafe_allow_html=True)

    # 2. ACTION BUTTONS & METRICS
    c_btn, c_m1, c_m2, c_m3 = st.columns([1.5, 1, 1, 1])
    
    with c_btn:
        st.write("") 
        if st.button("🔄 Quét ngay (AI Scan)", type="primary", use_container_width=True):
            with st.spinner("Đang gửi log tới AI Engine..."):
                time.sleep(1.5) # Giả lập gọi API backend
                st.session_state['last_scan_time'] = time.strftime("%H:%M:%S %d/%m/%Y")
                # Dữ liệu giả lập trả về từ AI
                st.session_state['threats_list'] = [
                    {"ip": "192.168.1.50", "type": "SQL Injection", "severity": "High", "time": "10:05:22"},
                    {"ip": "10.0.0.8", "type": "Brute Force", "severity": "Medium", "time": "10:06:01"},
                    {"ip": "45.33.12.99", "type": "Anomaly", "severity": "Low", "time": "10:15:00"},
                ]
                st.rerun()
                
    with c_m1: st.metric("AI Confidence", "99.7%")
    with c_m2: st.metric("Threshold", "0.85")
    with c_m3: st.metric("Processing", "12ms")

    # 3. DANH SÁCH CẢNH BÁO
    st.subheader("📋 Nhật ký Cảnh báo")
    threats = st.session_state['threats_list']
    
    if not threats:
        st.info("Hệ thống sạch. Nhấn 'Quét ngay' để kiểm tra lại.")
    else:
        # Header
        cols = st.columns([1, 2, 2, 2, 1.5])
        headers = ["Mức độ", "Thời gian", "Loại tấn công", "IP Nguồn", "Hành động"]
        for col, h in zip(cols, headers):
            col.markdown(f"**{h}**")
        st.divider()
        
        # Rows
        for t in threats:
            c1, c2, c3, c4, c5 = st.columns([1, 2, 2, 2, 1.5])
            
            # Badge logic
            badges = {"High": "🔴 Cao", "Medium": "🟠 TB", "Low": "🟡 Thấp"}
            
            with c1: st.write(badges.get(t['severity'], "⚪"))
            with c2: st.write(t['time'])
            with c3: st.write(f"**{t['type']}**")
            with c4: st.code(t['ip'])
            with c5: 
                if st.button("🚫 Block", key=f"blk_{t['ip']}"):
                    st.toast(f"Đã chặn IP {t['ip']}", icon="🛡️")
            
            st.markdown("<div class='alert-row'></div>", unsafe_allow_html=True)

        if st.button("Clear All Logs", type="secondary"):
            st.session_state['threats_list'] = []
            st.rerun()