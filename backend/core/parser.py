import re
import pandas as pd

# Regex chuẩn cho Combined Log Format
# Group names: ip, timestamp, request, status, size, referrer, user_agent
LOG_PATTERN = re.compile(
    r'(?P<ip>^[\d\.]+) \S+ \S+ \[(?P<timestamp>.*?)\] "(?P<request>.*?)" (?P<status>\d{3}) (?P<size>\S+) "(?P<referrer>.*?)" "(?P<user_agent>.*?)"'
)

def parse_log_file(filepath: str) -> pd.DataFrame:
    """
    Đọc file log và chuẩn hóa tên cột khớp với logic Training.
    Output columns cần thiết: [ip, datetime, method, path, status, size, referrer, user_agent]
    """
    data = []
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if not line.strip(): continue
                    
                match = LOG_PATTERN.match(line)
                if match:
                    row = match.groupdict()
                    
                    # 1. Tách Method và Path từ Request
                    # Input: "GET /index.php HTTP/1.1" -> Method: GET, Path: /index.php
                    parts = row['request'].split()
                    if len(parts) >= 2:
                        row['method'] = parts[0]
                        row['path'] = parts[1] # Code train dùng 'path', không dùng 'url'
                    else:
                        row['method'] = "unknown"
                        row['path'] = row['request']
                    
                    # 2. Xử lý Size (Dấu '-' convert thành 0)
                    row['size'] = 0 if row['size'] == '-' else int(row['size'])
                    
                    # 3. Rename timestamp -> datetime (cho khớp code train)
                    row['datetime'] = row.pop('timestamp')
                    
                    # Lưu ý: 'referrer' và 'user_agent' đã được đặt tên đúng trong Regex
                    data.append(row)

        df = pd.DataFrame(data)
        
        if df.empty:
            return pd.DataFrame()

        # 4. Đảm bảo Status là số
        df['status'] = pd.to_numeric(df['status'], errors='coerce').fillna(200)

        return df

    except Exception as e:
        print(f"❌ Lỗi Parser: {e}")
        return pd.DataFrame()