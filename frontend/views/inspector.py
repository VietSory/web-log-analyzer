import streamlit as st
import pandas as pd

def render_inspector():
    st.title("🔍 Raw Data Inspector")
    st.markdown("Công cụ tra cứu và lọc dữ liệu thô.")
    
    # Giả lập DataFrame (Sau này thay bằng st.session_state['analysis_data'])
    df_dummy = pd.DataFrame({
        'Timestamp': ['2023-10-10 10:00:01', '2023-10-10 10:00:02', '2023-10-10 10:00:05'],
        'IP Address': ['192.168.1.1', '10.0.0.5', '172.16.0.1'],
        'Method': ['GET', 'POST', 'GET'],
        'URL': ['/index.php', '/login', '/admin'],
        'Status': [200, 200, 403],  
        'User Agent': ['Mozilla/5.0...', 'Python-urllib...', 'Mozilla/5.0...']
    })

    # Khu vực bộ lọc (Filter)
    with st.expander("🛠️ Bộ lọc nâng cao", expanded=True):
        c1 , c2 = st.columns([1,3])
        with c1:
            search_ip = st.text_input("Tìm kiếm theo IP:", placeholder="VD: 192.168.1.1")
        with c2:
            filter_status = st.multiselect("Lọc theo Status Code:", 
                                         options=[200, 404, 500, 403], 
                                         default=[200, 404, 500, 403])
    
    # Logic lọc (Giả lập)
    if search_ip:
        st.caption(f"Đang hiển thị kết quả cho IP: {search_ip}")
    
    # Hiển thị bảng
    st.dataframe(df_dummy, use_container_width=True, height=600)