import streamlit as st
import pandas as pd
import requests
import time

st.set_page_config(page_title="Data Analyzer", 
                   page_icon="🛡️",
                   layout="wide",
                   initial_sidebar_state="expanded")

API_URL = "http://127.0.0.1:8000"

st.markdown("""
            <style>
            /* Ẩn Header mặc định của Streamlit */
            header {visibility: hidden;}
            .block-container {padding-top: 2rem;}
            
            /* Style cho Card trạng thái */
            .status-card {
                background-color: white;
                padding: 20px;
                border-radius: 15px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                text-align: center;
                margin-bottom: 20px;
            }
            
            /* Style cho mức độ nguy hiểm */
            .risk-badge {
                padding: 5px 10px;
                border-radius: 5px;
                font-weight: bold;
                color: white;
            }
        </style>
            """, unsafe_allow_html=True)
if 'current_filename' not in st.session_state:
    st.session_state["current_filename"] = None
if 'analysis_data' not in st.session_state:
    st.session_state["analysis_data"] = None
# PHẦN 1: SIDEBAR (Khu vực điều khiển)
with st.sidebar:
    st.header("Control Panel")
    st.write("---")
    st.subheader("📁 Upload Data File")
    uploaded_file = st.file_uploader("Upload your log here ", type=["csv", "txt", "log"])
    if uploaded_file is not None:
        if uploaded_file.name != st.session_state.get("last_uploaded_filename"):
            st.session_state["current_filename"] = None
        if st.button("🚀 Upload & Process", use_container_width=True):
            files = {"file": (uploaded_file.name, uploaded_file, "multipart/form-data")}
            with st.status("Đang xử lí dữ liệu, vui lòng đợi trong giây lát...",expanded=True) as status:
                try:
                    res = requests.post(f"{API_URL}/api/upload", files=files)
                    if res.status_code == 200:
                        st.session_state["current_filename"] = uploaded_file.name
                        st.session_state["last_uploaded_filename"] = uploaded_file.name
                        status.update(label = "Upload thành công!", state = "complete", expanded=False)
                        st.success(f"File ID: {uploaded_file.name}")
                    else:
                        status.update(label="Lỗi Server!", state="error")
                        st.error(res.text)
                except requests.exceptions.RequestException as e:
                    status.update(label="Mất kết nối Backend!", state="error", expanded=False)
                    st.error(f"Không thể gọi API: {e}")                    
    st.write("---")
    if st.session_state["current_filename"]:
        st.subheader("View Mode")
        view_mode = st.radio("Chọn chế độ xem:",
            ["📊 Dashboard Overview", "🔍 Raw Data Inspector", "🛡️ AI Security Monitor"])
    else:
        st.info("Vui lòng upload file để kích hoạt các chế độ xem.")
        view_mode = "Home"  
# PHẦN 2: MAIN PANEL (Khu vực hiển thị)
if view_mode == "Home":
    st.title("Chào mừng quản trị viên")
    st.markdown("""
                Chào mừng quay trở lại. Hệ thống đã sẵn sàng phân tích.
                **Quy trình làm việc:**
                1.  Tải file log lên từ Sidebar bên trái.
                2.  Hệ thống sẽ tự động chuẩn hóa dữ liệu.
                3.  Chọn các chế độ xem để phân tích sâu hơn.
                """)
elif view_mode == "📊 Dashboard Overview":
    st.title(f"📊 Dashboard: {st.session_state['current_filename']}")
    st.markdown("Tổng quan hệ thống dựa trên dữ liệu log.")    
    filename = st.session_state["current_filename"]
    try:
        with st.spinner("Đang tải dữ liệu..."):
            time.sleep(1)  # Giả lập độ trễ mạng
            col1, col2 , col3, col4 = st.columns(4)
            col1.metric("Total Requests", "15,204", "+12%")
            col2.metric("Unique IPs", "342", "-5%")
            col3.metric("Avg Body Size", "24 KB", "0%")
            col4.metric("Error Rate (5xx)", "1.2%", "Normal")
            st.divider()
            
            c1,c2 = st.columns(2)
            with c1:
                c1.subheader("Traffic Over Time")
                chart_data = pd.DataFrame({
                    'Time': pd.date_range(start='1/1/2024', periods=24, freq='H'),
                    'requests': [10, 20, 50, 40, 90, 120, 150, 200, 180, 100, 50, 30] * 2
                })
                st.line_chart(chart_data.set_index('Time'))
            with c2:
                st.subheader("Status Code")
                status_data = pd.DataFrame({
                    'Status': ['200 OK', '404 Not Found', '500 Error', '301 Redirect'],
                    'Count': [12000, 2500, 300, 404]
                })
                st.bar_chart(status_data.set_index('Status'))
    except Exception as e:
        st.error(f"Lỗi khi tải dữ liệu: {e}")
        
elif view_mode == "Log Inspector":
    st.title("🔍 Raw Data Inspector")
    st.markdown("Xem và lọc dữ liệu thô để điều tra thủ công.")
    
    # Giả lập DataFrame
    df_dummy = pd.DataFrame({
        'Timestamp': ['2023-10-10 10:00:01', '2023-10-10 10:00:02', '2023-10-10 10:00:05'],
        'IP Address': ['192.168.1.1', '10.0.0.5', '172.16.0.1'],
        'Method': ['GET', 'POST', 'GET'],
        'URL': ['/index.php', '/login', '/admin'],
        'Status': [200, 200, 403],
        'User Agent': ['Mozilla/5.0...', 'Python-urllib...', 'Mozilla/5.0...']
    })
    c1 , c2 = st.columns([1,3])
    with c1:
        search_ip = st.text_input("Tìm kiếm theo IP:", placeholder="VD: 192.168.1.1")
    with c2:
        filter_status = st.multiselect("Lọc theo Status Code:", options=[200, 404, 500, 403], default=[200, 404, 500, 403])
    st.dataframe(df_dummy , use_container_width=True, height=500)

elif view_mode == "🛡️ AI Security Monitor":
    st.markdown("""
        <style>
            /* Box trạng thái hệ thống */
            .system-status-box {
                padding: 20px;
                border-radius: 8px;
                margin-bottom: 20px;
                border: 1px solid #e0e0e0;
                display: flex;
                align-items: center;
                justify-content: space-between;
            }
            /* Định dạng các thẻ metric nhỏ */
            div[data-testid="stMetric"] {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                padding: 10px;
                border-radius: 5px;
            }
            /* Hàng tiêu đề của danh sách cảnh báo */
            .alert-header {
                font-weight: bold;
                color: #495057;
                padding-bottom: 10px;
                border-bottom: 2px solid #e9ecef;
                margin-bottom: 10px;
            }
        </style>
    """, unsafe_allow_html=True)

    st.title("🛡️ Phát hiện bất thường Hệ thống")
    st.markdown("Phát hiện bất thường dựa trên AI (Deep Learning Analysis).")
    if 'last_scan_time' not in st.session_state:
        st.session_state['last_scan_time'] = "Chưa quét"
    if 'threats_list' not in st.session_state:
        st.session_state['threats_list'] = []
    
    # 1. TRẠNG THÁI HỆ THỐNG (STATUS BANNER)
    threat_count = len(st.session_state['threats_list'])    
    if threat_count == 0:
        status_color = "#d4edda" 
        text_color = "#155724"   
        border_color = "#c3e6cb"
        status_icon = "✅"
        status_title = "Hệ thống hoạt động bình thường"
        status_desc = "Không phát hiện mối đe dọa nào trong lần quét gần nhất."
    else:
        status_color = "#f8d7da"
        text_color = "#721c24"   
        border_color = "#f5c6cb"
        status_icon = "🚨"
        status_title = f"CẢNH BÁO: Phát hiện {threat_count} mối đe dọa"
        status_desc = "Vui lòng kiểm tra danh sách bên dưới và thực hiện biện pháp ngăn chặn."
    st.markdown(f"""
        <div class="system-status-box" style="background-color: {status_color}; color: {text_color}; border-color: {border_color};">
            <div>
                <h3 style="margin: 0; padding: 0; color: {text_color};">{status_icon} {status_title}</h3>
                <p style="margin: 5px 0 0 0; opacity: 0.9;">{status_desc}</p>
            </div>
            <div style="text-align: right; font-size: 0.9em;">
                <strong>Lần quét cuối:</strong><br>{st.session_state['last_scan_time']}
            </div>
        </div>
    """, unsafe_allow_html=True)
    c_btn, c_m1, c_m2, c_m3 = st.columns([1.5, 1, 1, 1])
    
    with c_btn:
        st.write("") # Spacer căn chỉnh
        # Nút bấm chính: To, rõ ràng, màu sắc chuyên nghiệp
        if st.button("🔄 Quét ngay (Quick Scan)", type="primary", use_container_width=True):
            with st.spinner("Đang phân tích log máy chủ..."):
                time.sleep(1)                 
                st.session_state['last_scan_time'] = time.strftime("%H:%M:%S %d/%m/%Y")
                st.session_state['threats_list'] = [
                    {"ip": "192.168.1.50", "type": "SQL Injection", "severity": "High", "time": "10:05:22"},
                    {"ip": "10.0.0.8", "type": "Brute Force", "severity": "Medium", "time": "10:06:01"},
                    {"ip": "45.33.12.99", "type": "Unknown Anomaly", "severity": "Low", "time": "10:15:00"},
                ]
                st.rerun()
                
    with c_m1:
        st.metric("Tổng Request", "15.2K")
    with c_m2:
        st.metric("Lưu lượng", "120 req/s")
    with c_m3:
        st.metric("Độ tin cậy AI", "99.7%")

    st.write("---")
    st.subheader("📋 Nhật ký Cảnh báo An ninh")
    threats = st.session_state['threats_list']
    if not threats:
        st.info("Chưa có dữ liệu cảnh báo. Vui lòng nhấn nút 'Quét ngay' để kiểm tra hệ thống.")
    else:
        # Tiêu đề bảng (Header)
        col_h1, col_h2, col_h3, col_h4, col_h5 = st.columns([1, 2, 2, 1.5, 1.5])
        col_h1.markdown("**Mức độ**")
        col_h2.markdown("**Thời gian**")
        col_h3.markdown("**Loại tấn công**")
        col_h4.markdown("**IP Nguồn**")
        col_h5.markdown("**Hành động**")
        st.divider()
        # Render từng dòng dữ liệu (Row)
        for t in threats:
            c1, c2, c3, c4, c5 = st.columns([1, 2, 2, 1.5, 1.5])
            if t['severity'] == "High":
                severity_badge = "🔴 Cao"
            elif t['severity'] == "Medium":
                severity_badge = "🟠 TB"
            else:
                severity_badge = "🟡 Thấp"
            with c1: st.write(severity_badge)
            with c2: st.write(t['time'])
            with c3: st.write(f"**{t['type']}**")
            with c4: st.code(t['ip'])
            with c5: 
                if st.button("🚫 Chặn IP", key=f"blk_{t['ip']}"):
                    st.toast(f"Đã thêm IP {t['ip']} vào danh sách đen (Blacklist).", icon="shield")
            st.markdown("<div style='margin-bottom: 5px; border-bottom: 1px solid #f0f0f0;'></div>", unsafe_allow_html=True)
        st.write("")
        if st.button("Đánh dấu đã xử lý xong (Clear All)"):
            st.session_state['threats_list'] = []
            st.rerun()