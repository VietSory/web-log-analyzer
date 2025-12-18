# FILE: frontend/views/history.py
import streamlit as st
import pandas as pd
import requests
import time
from utils import API_URL, load_custom_css
def render_history():
    load_custom_css()
    st.title("📜 Thư viện Báo cáo")
    try:
        res = requests.get(f"{API_URL}/api/history")
        history_data = res.json() if res.status_code == 200 else []
    except:
        st.error("🔌 Mất kết nối tới Backend.")
        return
    with st.sidebar:
        st.divider()
        st.header("⚠️ Quản lý Dữ liệu")
        
        with st.expander("🧨 Xóa toàn bộ dữ liệu", expanded=False):
            st.warning("Hành động này sẽ xóa TOÀN BỘ lịch sử quét.")
            
            if st.button("Xác nhận Xóa SẠCH", type="primary", use_container_width=True):
                with st.spinner("Đang dọn dẹp database..."):
                    try:
                        # Gọi API xóa tất cả
                        res = requests.delete(f"{API_URL}/api/history/clear-all")
                        if res.status_code == 200:
                            st.toast("✅ Đã xóa sạch dữ liệu! ID đã reset.", icon="🗑️")
                            time.sleep(1.5)
                            st.rerun() 
                        else:
                            st.error(f"Lỗi Server: {res.text}")
                    except Exception as e:
                        st.error(f"Lỗi kết nối: {e}")
                        
    if not history_data:
        st.info("📭 Chưa có lịch sử quét nào.")
        return

    df_hist = pd.DataFrame(history_data)
    df_hist['display_label'] = df_hist.apply(
        lambda x: f"ID {x['id']} | {x['filename']} | {x['scan_date']}", axis=1
    )
    with st.container():
        c_search, c_stats = st.columns([3, 1])
        with c_search:
            search_query = st.text_input(
                "🔍 Tìm kiếm báo cáo:", 
                placeholder="Nhập tên file, ngày (2025-12...) hoặc ID...",
                help="Lọc danh sách theo Tên file hoặc Thời gian"
            )
        with c_stats:
            st.metric("Tổng báo cáo", len(df_hist), label_visibility="visible")
    if search_query:
        df_filtered = df_hist[
            df_hist['filename'].str.contains(search_query, case=False) | 
            df_hist['scan_date'].str.contains(search_query, case=False) |
            df_hist['id'].astype(str).str.contains(search_query)
        ]
    else:
        df_filtered = df_hist
    with st.container(border=True):
        st.subheader(f"🗂️ Danh sách ({len(df_filtered)} kết quả)") 
        st.dataframe(
            df_filtered,
            column_config={
                "id": st.column_config.NumberColumn("ID", width="small"),
                "filename": st.column_config.TextColumn("Tên File", width="medium"),
                "scan_date": st.column_config.TextColumn("Thời gian lưu", width="medium"),
                "total_requests": st.column_config.NumberColumn("Reqs", help="Tổng số request"),
                "error_rate": st.column_config.NumberColumn("Lỗi %", format="%.2f%%"),
                "display_label": None 
            },
            use_container_width=True,
            hide_index=True,
            height=300
        )
    st.write("") 

    if df_filtered.empty:
        st.warning("⚠️ Không tìm thấy báo cáo nào khớp với từ khóa.")
    else:
        c_select, c_btn_view, c_btn_del = st.columns([3, 1, 1], gap="small")
        with c_select:
            selected_label = st.selectbox(
                "Chọn báo cáo để thao tác:", 
                df_filtered['display_label'], 
                index=0,
                label_visibility="collapsed"
            )
            selected_id = int(selected_label.split("|")[0].replace("ID", "").strip())
        with c_btn_view:
            btn_view = st.button("📂 Xem Chi tiết", type="primary", use_container_width=True)
        with c_btn_del:
            if st.button("🗑️ Xóa", type="secondary", use_container_width=True):
                try:
                    res = requests.delete(f"{API_URL}/api/history/{selected_id}")
                    if res.status_code == 200:
                        st.toast(f"✅ Đã xóa báo cáo ID {selected_id}", icon="🗑️")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Xóa thất bại.")
                except Exception as e:
                    st.error(f"Lỗi: {e}")
        if btn_view:
            with st.spinner("Đang tải dữ liệu báo cáo..."):
                try:
                    res_det = requests.get(f"{API_URL}/api/history/{selected_id}")
                    if res_det.status_code == 200:
                        detail = res_det.json()
                        render_report_detail(detail)
                    else:
                        st.error("⚠️ Không tìm thấy dữ liệu báo cáo này.")
                except Exception as e:
                    st.error(f"Lỗi kết nối: {e}")

def render_report_detail(detail):
    st.divider()
    st.markdown(f"### 📊 Báo cáo chi tiết: `{detail['filename']}`")
    st.caption(f"🕒 Thời gian lưu: {detail['scan_date']}")
    # 1. Thống kê
    k1, k2, k3 = st.columns(3)
    k1.metric("Tổng Requests", f"{detail['total_requests']:,}", border=True)
    k2.metric("IP Duy nhất", f"{detail['unique_ips']:,}", border=True)
    err = detail['error_rate']
    k3.metric("Tỷ lệ Lỗi (5xx)", f"{err}%", delta_color="inverse" if err > 5 else "normal", border=True)

    # 2. Biểu đồ
    c1, c2 = st.columns([2, 1])
    with c1:
        st.markdown("**📈 Lưu lượng theo giờ**")
        tf_chart = detail.get('traffic_chart', {})
        if tf_chart:
            df_tf = pd.DataFrame(list(tf_chart.items()), columns=['Time', 'Requests'])
            df_tf['Time'] = pd.to_datetime(df_tf['Time'])
            st.line_chart(df_tf.set_index('Time').sort_index(), color="#00FF00", height=200)
        else:
            st.info("Không có dữ liệu biểu đồ.")
    with c2:
        st.markdown("**🍩 Mã trạng thái**")
        st_chart = detail.get('status_distribution', {})
        if st_chart:
            st.bar_chart(pd.DataFrame(list(st_chart.items()), columns=['Code', 'Count']).set_index('Code'), height=200)

    # 3. Danh sách mối đe dọa
    st.subheader("🚨 Nhật ký Mối đe dọa")
    saved_threats = detail.get('threats', [])
    if saved_threats:
        with st.container(border=True):
            st.error(f"Phát hiện {len(saved_threats)} hành vi bất thường.")
            df_t = pd.DataFrame(saved_threats)
            df_show = df_t[['time', 'ip', 'reconstruction_error', 'details']].copy()
            st.dataframe(
                df_show,
                use_container_width=True,
                column_config={
                    "time": st.column_config.TextColumn("Thời gian", width="medium"),
                    "ip": st.column_config.TextColumn("IP Nguồn", width="medium"),
                    "reconstruction_error": st.column_config.ProgressColumn(
                        "Mức độ rủi ro (Loss)", format="%.4f", min_value=0, max_value=0.5
                    ),
                    "details": st.column_config.TextColumn("Chi tiết đường dẫn", width="large")
                },
                hide_index=True
            )
    else:
        st.success("✅ Báo cáo này sạch.")