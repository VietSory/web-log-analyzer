import streamlit as st
import pandas as pd
import requests
from utils import API_URL

def render_inspector():
    filename = st.session_state.get("current_filename", "Unknown")
    st.title("🔍 Raw Data Inspector")
    st.markdown(f"Công cụ tra cứu dữ liệu thô cho file: **{filename}**")
    if filename == "Unknown" or not filename:
        st.warning("Vui lòng upload file trước.")
        return
    if 'raw_logs' not in st.session_state or st.session_state.get('last_log_file') != filename:
        with st.spinner("Đang tải dữ liệu log chi tiết..."):
            try:
                res = requests.get(f"{API_URL}/api/logs/{filename}")
                if res.status_code == 200:
                    st.session_state['raw_logs'] = pd.DataFrame(res.json())
                    st.session_state['last_log_file'] = filename
                else:
                    st.error(f"Lỗi tải dữ liệu: {res.text}")
                    return
            except Exception as e:
                st.error(f"Không thể kết nối Backend: {e}")
                return

    df = st.session_state['raw_logs']

    if df.empty:
        st.info("File log rỗng hoặc không phân tích được dữ liệu.")
        return
    with st.expander("🛠️ Bộ lọc nâng cao", expanded=True):
        c1, c2 = st.columns([1, 3])
        with c1:
            search_ip = st.text_input("Tìm kiếm theo IP:", placeholder="VD: 192.168.1.1")
        with c2:
            available_status = sorted(df['status'].unique()) if 'status' in df.columns else []
            filter_status = st.multiselect(
                "Lọc theo Status Code:", 
                options=available_status
            )
    df_display = df.copy()
    if search_ip:
        if 'ip' in df_display.columns:
            # Lọc chứa chuỗi (contains), case=False để không phân biệt hoa thường
            df_display = df_display[df_display['ip'].astype(str).str.contains(search_ip, case=False, na=False)]
        else:
            st.warning("Không tìm thấy cột IP trong dữ liệu.")

    # Lọc theo Status Code
    if filter_status:
        if 'status' in df_display.columns:
            df_display = df_display[df_display['status'].isin(filter_status)]

    st.caption(f"Đang hiển thị {len(df_display)} / {len(df)} dòng log.")
    
    # Sắp xếp lại cột cho dễ nhìn (nếu cột tồn tại)
    priority_cols = ['datetime', 'ip', 'method', 'path', 'status', 'size']
    cols_to_show = [c for c in priority_cols if c in df_display.columns]
    cols_to_show += [c for c in df_display.columns if c not in cols_to_show]
    
    st.dataframe(
        df_display[cols_to_show], 
        use_container_width=True, 
        height=600,
        column_config={
            "datetime": st.column_config.TextColumn("Time"),
            "ip": st.column_config.TextColumn("IP Address"),
            "status": st.column_config.NumberColumn("Status", format="%d"),
            "size": st.column_config.NumberColumn("Size (B)", format="%d"),
        }
    )