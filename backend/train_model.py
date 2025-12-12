import os
import re
import numpy as np
import pandas as pd
import joblib

import tensorflow as tf
from tensorflow.keras.models import Model # type: ignore
from tensorflow.keras.layers import Input, Dense # type: ignore

from sklearn.preprocessing import MinMaxScaler, LabelEncoder

DATA_FILE = "./training_data.csv" 
OUTPUT_DIR = "./models/"            
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Regex Parser (Đồng bộ với Backend)
LOG_PATTERN = re.compile(
    r'(?P<ip>^[\d\.]+) \S+ \S+ \[(?P<timestamp>.*?)\] "(?P<request>.*?)" (?P<status>\d{3}) (?P<size>\S+) "(?P<referrer>.*?)" "(?P<user_agent>.*?)"\s*.*'
)

def parse_log_for_train(filepath):
    print(f"⏳ Đang đọc file log: {filepath}...")
    data = []
    
    if not os.path.exists(filepath):
        print(f"❌ Lỗi: Không tìm thấy file {filepath}")
        return pd.DataFrame()

    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                match = LOG_PATTERN.match(line.strip())
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
                    
                    row['size'] = 0 if row['size'] == '-' else int(row['size'])
                    row['status'] = int(row['status'])
                    
                    # Trích xuất giờ
                    try:
                        # Kiểm tra sơ bộ để tránh lỗi parse
                        if "Jan" in row['timestamp'] or "Feb" in row['timestamp']: 
                            dt = pd.to_datetime(row['timestamp'], format='%d/%b/%Y:%H:%M:%S %z', errors='coerce')
                            row['hour'] = dt.hour if pd.notnull(dt) else 0
                        else:
                            # Fallback nếu format timestamp khác
                            row['hour'] = 0
                    except:
                        row['hour'] = 0
                        
                    data.append(row)
    except Exception as e:
        print(f"❌ Lỗi khi đọc file: {e}")
        return pd.DataFrame()
    
    return pd.DataFrame(data)

def train():
    # 1. Load Data
    df = parse_log_for_train(DATA_FILE)
    print(f"✅ Đã chuẩn bị {len(df)} dòng dữ liệu.")

    # 2. Label Encoding
    cols_to_encode = ['ip', 'method', 'path', 'referrer', 'user_agent']
    label_encoders = {}
    
    for col in cols_to_encode:
        le = LabelEncoder()
        if col not in df.columns: df[col] = "unknown"
        df[col] = df[col].astype(str)
        
        # Fit & Transform
        df[col + '_enc'] = le.fit_transform(df[col])
        label_encoders[col] = le
        
    print("✅ Đã mã hóa Text sang Số.")

    # 3. Prepare Vector (8 features)
    feature_cols = ['ip_enc', 'method_enc', 'path_enc', 'status', 'size', 'referrer_enc', 'user_agent_enc', 'hour']
    
    # Đảm bảo đủ cột
    for col in feature_cols:
        if col not in df.columns:
            df[col] = 0

    X = df[feature_cols].values.astype(np.float32)

    # 4. Scaling
    scaler = MinMaxScaler()
    X_scaled = scaler.fit_transform(X)
    print("✅ Đã chuẩn hóa (Scaling).")

    # 5. Build Autoencoder Model (Sử dụng cách import trực tiếp)
    input_dim = X_scaled.shape[1] # 8
    
    input_layer = Input(shape=(input_dim,))
    
    # Encoder
    encoded = Dense(16, activation='relu')(input_layer)
    encoded = Dense(8, activation='relu')(encoded)
    
    # Decoder
    decoded = Dense(16, activation='relu')(encoded)
    output_layer = Dense(input_dim, activation='sigmoid')(decoded)

    autoencoder = Model(inputs=input_layer, outputs=output_layer)
    autoencoder.compile(optimizer='adam', loss='mse')

    # 6. Training
    print("🚀 Bắt đầu Train (100 epochs)...")
    autoencoder.fit(
        X_scaled, X_scaled,
        epochs=100,
        batch_size=128,
        shuffle=True,
        validation_split=0.1,
        verbose=1 # Tắt log chi tiết để đỡ rối
    )

    # 7. Tính Threshold
    reconstructions = autoencoder.predict(X_scaled)
    mse = np.mean(np.power(X_scaled - reconstructions, 2), axis=1)
    threshold = np.mean(mse) + 4 * np.std(mse)
    
    print(f"🎯 Ngưỡng phát hiện (Threshold): {threshold:.6f}")

    # 8. Lưu file
    autoencoder.save(os.path.join(OUTPUT_DIR, 'autoencoder_model.keras'))
    joblib.dump(scaler, os.path.join(OUTPUT_DIR, 'scaler.pkl'))
    joblib.dump(label_encoders, os.path.join(OUTPUT_DIR, 'label_encoders.pkl'))
    joblib.dump(threshold, os.path.join(OUTPUT_DIR, 'reconstruction_threshold.pkl'))

    print("\n🎉 TRAINING THÀNH CÔNG!")
    print(f"👉 4 file model đã được lưu tại: {OUTPUT_DIR}")

if __name__ == "__main__":
    train()