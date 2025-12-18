# 🛡️ AI Web Log Analyzer - Hệ thống Giám sát An ninh Log

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-Frontend-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![TensorFlow](https://img.shields.io/badge/AI-TensorFlow%2FKeras-FF6F00?style=for-the-badge&logo=tensorflow&logoColor=white)
![Status](https://img.shields.io/badge/Status-Active-success?style=for-the-badge)

> **Giải pháp phân tích Log máy chủ web tự động sử dụng mô hình Deep Learning (Autoencoder) kết hợp với luật (Rule-based) để phát hiện bất thường trong log từ đó định danh các cuộc tấn công mạng.**

## 📑 Mục lục
- [Giới thiệu](#-giới-thiệu)
- [Tính năng nổi bật](#-tính-năng-nổi-bật)
- [Cấu trúc dự án](#-cấu-trúc-dự-án)
- [Cài đặt & Khởi chạy](#-cài-đặt--khởi-chạy)
- [Hướng dẫn sử dụng](#-hướng-dẫn-sử-dụng)
- [Công nghệ sử dụng](#-công-nghệ-sử-dụng)

---

## 📖 Giới thiệu

**Web Log Analyzer** là công cụ hỗ trợ Quản trị viên hệ thống (SysAdmin) trong việc giám sát nhật ký truy cập (Access Logs).
Khác với các công cụ truyền thống chỉ dựa trên luật (Signature-based), hệ thống này áp dụng phương pháp tiếp cận lai (**Hybrid Approach**):
1.  **AI (Autoencoder):** Học hành vi bình thường để phát hiện các bất thường chưa biết (Unknown Threats/Zero-day).
---

## 🚀 Tính năng nổi bật

* **📂 Quản lý Đa nguồn dữ liệu:** Hỗ trợ upload và xử lý hàng loạt file log cùng lúc. Chuyển đổi linh hoạt giữa các file để phân tích.
* **🧠 AI Anomaly Detection:** Tự động tính toán điểm bất thường (Loss Score) cho từng request bằng mô hình Autoencoder.
* **📊 Dashboard Trực quan:** Biểu đồ Time-series, phân bố mã lỗi (Status Codes) và thống kê nhanh.
* **📜 Thư viện Báo cáo (History):**
    * Lưu trữ kết quả quét vào cơ sở dữ liệu.
    * Xem lại chi tiết, so sánh và xóa báo cáo cũ.
    * Tìm kiếm/Lọc báo cáo theo tên file hoặc ngày tháng.
* **🎨 Giao diện Hiện đại:** UI tối ưu với Dark Mode, thanh tiến trình rủi ro và Badges cảnh báo.

---

## 📂 Cấu trúc dự án

```text
web-log-analyzer/
├── backend/                  # Xử lý Logic & API (FastAPI)
│   ├── core/
│   │   ├── ml_engine.py      # AI Class (Load model, Detect anomalies)
│   │   └── parser.py         # Log Parser & Attack Classification
│   ├── models/               # Chứa file model đã train (.keras, .pkl)
│   ├── routers/              # API Endpoints (Scan, Upload, Stats, History)
│   ├── uploads/              # Thư mục lưu trữ file tạm
│   ├── database.py           # Quản lý SQLite (CRUD History)
│   ├── main.py               # Entry point của Backend
|   ├── requirements.txt      # Các thư viện phụ thuộc
|   ├── train_model.py        # File để chạy train model AI tạo ra các file cần thiết
│   └── weblog_analyzer.db    # SQLite Database
├── frontend/                 # Giao diện người dùng (Streamlit)
│   ├── assets/               # Tài nguyên tĩnh (CSS, Images)
│   ├── views/                # Các trang chức năng
│   │   ├── home.py           # Trang chủ
│   │   ├── dashboard.py      # Thống kê
│   │   ├── ml_inspector.py   # Màn hình quét AI (AI Monitor)
│   │   ├── history.py        # Quản lý lịch sử báo cáo
│   │   └── inspector.py      # Soi log thô
│   ├── app.py                # Entry point của Frontend
|   ├── requirements.txt      # Các thư viện phụ thuộc
│   └── utils.py              # Hàm tiện ích chung
├── .gitignor                 # Bỏ qua các file dev không muốn up lên git
└── README.md                 # Tài liệu hướng dẫn
```
## 🛠 Cài đặt & Khởi chạy
**1. Yêu cầu môi trường**
Python: Phiên bản 3.10 trở lên.

Thư viện: Cài đặt theo file requirements.txt.

```bash
pip install -r requirements.txt
```
**2. Khởi chạy các file model cần thiết**
Mở terminal tại thư mục backend/:

```bash
cd backend
python train_model.py
```

**3. Khởi chạy Backend (API Server)**
Mở terminal tại thư mục backend/:

```bash
cd backend
python main.py
```

Server sẽ khởi động tại: http://127.0.0.1:8000 và tự động khởi tạo Database.

**4. Khởi chạy Frontend (User Interface)**
Mở một terminal khác tại thư mục gốc dự án:

```bash
cd frontend
streamlit run app.py
```
Giao diện sẽ tự động mở trên trình duyệt tại: http://localhost:8501

## 📖 Hướng dẫn sử dụng

### Upload Log Files
Step 1: Vào Sidebar bên trái, chọn mục Upload Log Files  
Step 2: Chọn hoặc kéo–thả một hoặc nhiều file log  
Step 3: Nhấn 🚀 Xử lý để bắt đầu phân tích  

### Chọn File phân tích
- Sử dụng Selectbox trong Sidebar để chọn file log cần làm việc (nếu upload nhiều file)

### Xem Tổng quan (Dashboard)
- Xem biểu đồ traffic theo thời gian và tỷ lệ lỗi để nắm bắt tình hình hệ thống

### Phát hiện Tấn công (AI Monitor)
Step 1: Chuyển sang tab 🛡️ AI Monitor  
Step 2: Nhấn 🔄 QUÉT NGAY để chạy AI kết hợp Rule-based detection  
Step 3: Xem danh sách các request đáng ngờ hoặc nguy hiểm được phát hiện  

### Lưu trữ & Tra cứu
Step 1: Nhấn 💾 Lưu vào Lịch sử để lưu kết quả phân tích  
Step 2: Truy cập tab 📜 History để tìm kiếm, xem lại hoặc xóa các báo cáo cũ  

## 💻 Công nghệ sử dụng
- Backend: FastAPI (Python)
- Frontend: Streamlit
- AI Core: TensorFlow / Keras (Autoencoder Neural Network)
- Preprocessing: Scikit-learn (MinMaxScaler, LabelEncoder)
- Database: SQLite
