# Web Log Analyzer - Mail Service Configuration

## Cấu hình Mail Service

Mail service sẽ tự động gửi email cảnh báo khi phát hiện log warning.

### 1. Cấu hình cho Gmail

#### Bước 1: Tạo App Password

1. Truy cập: https://myaccount.google.com/security
2. Bật "2-Step Verification" (xác thực 2 bước)
3. Vào "App passwords": https://myaccount.google.com/apppasswords
4. Chọn app: "Mail", device: "Other" → nhập "Web Log Analyzer"
5. Copy mã 16 ký tự được tạo ra

#### Bước 2: Tạo file `.env`

```bash
cd backend
cp .env.example .env
```

#### Bước 3: Chỉnh sửa `.env`

```bash
MAIL_ENABLED=true
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=xxxx-xxxx-xxxx-xxxx  # App Password 16 ký tự
FROM_EMAIL=your-email@gmail.com
ALERT_EMAIL=admin@example.com      # Email nhận cảnh báo
```

### 2. Cấu hình cho Outlook/Hotmail

```bash
MAIL_ENABLED=true
SMTP_SERVER=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_USER=your-email@outlook.com
SMTP_PASSWORD=your-password
FROM_EMAIL=your-email@outlook.com
ALERT_EMAIL=admin@example.com
```

### 3. Cấu hình cho SMTP Server tùy chỉnh

```bash
MAIL_ENABLED=true
SMTP_SERVER=mail.your-domain.com
SMTP_PORT=587
SMTP_USER=noreply@your-domain.com
SMTP_PASSWORD=your-smtp-password
FROM_EMAIL=noreply@your-domain.com
ALERT_EMAIL=admin@your-domain.com
```

### 4. Test Mail Service

```bash
cd backend
python test_mail.py
```

### 5. Sử dụng

Mail sẽ tự động được gửi khi:

- API `/api/servers/{server_id}/analyze` phát hiện log có status `warning`
- Email sẽ chứa:
  - Thông tin server (name, ID)
  - Nội dung log đầy đủ
  - Chi tiết anomaly (IP, severity, reconstruction error)
  - Thời gian phát hiện

### 6. Tắt Mail Service

Để tắt tạm thời mà không xóa cấu hình:

```bash
MAIL_ENABLED=false
```

### 7. Template Email

Email gửi đi sẽ có format HTML đẹp mắt với:

- Header màu đỏ cảnh báo
- Bảng thông tin server
- Log content với background màu tối
- Chi tiết anomaly (nếu có)
- Footer với timestamp

### Troubleshooting

**Lỗi: Authentication failed**

- Kiểm tra SMTP_USER và SMTP_PASSWORD
- Gmail: phải dùng App Password, không phải password thường
- Outlook: có thể cần bật "Less secure app access"

**Lỗi: Connection timeout**

- Kiểm tra SMTP_SERVER và SMTP_PORT
- Kiểm tra firewall/network có chặn port 587 không

**Email không nhận được**

- Kiểm tra spam folder
- Kiểm tra ALERT_EMAIL đúng chưa
- Xem logs backend để biết email có gửi thành công không
