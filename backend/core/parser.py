import re
import pandas as pd

LOG_PATTERN = re.compile(
    r'(?P<ip>^[\d\.]+) \S+ \S+ \[(?P<timestamp>.*?)\] "(?P<request>.*?)" (?P<status>\d{3}) (?P<size>\S+) "(?P<referrer>.*?)" "(?P<user_agent>.*?)"\s*.*'
)

def parse_log_file(filepath: str) -> pd.DataFrame:
    data = []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if not line: continue
                
                match = LOG_PATTERN.match(line)
                if match:
                    row = match.groupdict()
                    # Tách Method/Path
                    parts = row['request'].split()
                    if len(parts) >= 2:
                        row['method'] = parts[0]
                        row['path'] = parts[1]
                    else:
                        row['method'] = "unknown"
                        row['path'] = row['request']
                    # Xử lý Size
                    row['size'] = 0 if row['size'] == '-' else int(row['size'])                    
                    row['datetime'] = row.pop('timestamp')
                    data.append(row)

        df = pd.DataFrame(data)
        if df.empty: return pd.DataFrame()
        # Ép kiểu dữ liệu 
        df['status'] = pd.to_numeric(df['status'], errors='coerce').fillna(200)
        df['datetime'] = pd.to_datetime(df['datetime'], format='%d/%b/%Y:%H:%M:%S %z', errors='coerce')
        
        return df

    except Exception as e:
        print(f"❌ Lỗi Parser: {e}")
        return pd.DataFrame()