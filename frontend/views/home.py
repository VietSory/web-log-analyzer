import streamlit as st

def render_home_page():
    st.title("👋 Chào mừng Quản trị viên")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        ### Hệ thống Phân tích Log & Phát hiện Tấn công AI
        
        Hệ thống này giúp bạn giám sát an ninh mạng dựa trên phân tích Log máy chủ.
        
        **Quy trình làm việc chuẩn:**
        1.  📂 **Upload:** Tải file log (CSV/TXT) ở thanh bên trái.
        2.  📊 **Overview:** Xem thống kê tổng quan về lưu lượng.
        3.  🛡️ **AI Monitor:** Quét và phát hiện tấn công.
        4.  🔍 **Inspector:** Truy vết chi tiết từng dòng log.
        """)
        
        st.info("💡 Mẹo: Hãy bắt đầu bằng việc upload file log mẫu 'access_log.csv'.")

    with col2:
        st.image("https://cdn-icons-png.flaticon.com/512/2092/2092663.png", width=150)