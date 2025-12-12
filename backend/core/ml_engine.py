import os
import numpy as np
import pandas as pd
import joblib
from datetime import datetime

class LogAnomalyDetector:
    def __init__(self, model_dir: str):
        self.model_dir = model_dir
        self.model = None
        self.scaler = None
        self.label_encoders = None
        self.threshold = None 

    def load_resources(self):
        print(f"--- Loading AI Resources from {self.model_dir} ---")
        
        # 1. Load Model (.keras)
        try:
            from tensorflow.keras.models import load_model # type: ignore
            
            model_path = os.path.join(self.model_dir, 'autoencoder_model.keras')
            if os.path.exists(model_path):
                self.model = load_model(model_path)
                print(f"✅ Model loaded: {model_path}")
            else:
                print(f"❌ Model not found: {model_path}")
        except Exception as e:
            print(f"❌ Error loading Model: {e}")

        # 2. Load Scaler, LabelEncoders, Threshold
        try:
            scaler_path = os.path.join(self.model_dir, 'scaler.pkl')
            le_path = os.path.join(self.model_dir, 'label_encoders.pkl')
            th_path = os.path.join(self.model_dir, 'reconstruction_threshold.pkl')

            if os.path.exists(scaler_path):
                self.scaler = joblib.load(scaler_path)
                print("✅ Scaler loaded")
            
            if os.path.exists(le_path):
                self.label_encoders = joblib.load(le_path)
                print("✅ Label Encoders loaded")

            # --- LOGIC MỚI CHO THRESHOLD ---
            if os.path.exists(th_path):
                # Load từ file train (Chính xác nhất)
                self.threshold = joblib.load(th_path)
                print(f"✅ Threshold loaded from Train Model: {self.threshold:.6f}")
            else:
                # Fallback nếu không có file
                self.threshold = 0.05
                print(f"⚠️ Threshold file not found. Using default fallback: {self.threshold}")
                
        except Exception as e:
            print(f"❌ Error loading Pickle files: {e}")
            # Đảm bảo threshold luôn có giá trị để không crash
            if self.threshold is None: self.threshold = 0.05

    def safe_label_transform(self, encoder, values):
        """Xử lý giá trị lạ (New IP/Url) an toàn để không bị crash."""
        classes = list(encoder.classes_)
        val_map = {val: idx for idx, val in enumerate(classes)}
        # Nếu không tìm thấy giá trị, trả về 0
        return [val_map.get(str(x), 0) for x in values]

    def preprocess_features(self, df: pd.DataFrame):
        """Chuyển đổi DataFrame Log thành Input Vector (8 đặc trưng)."""
        if df.empty or self.model is None or self.scaler is None:
            return None, None

        features = df.copy()

        # 1. Xử lý Thời gian (Hour)
        if 'datetime' in features.columns:
            time_col = pd.to_datetime(features['datetime'], errors='coerce')
            features['hour'] = time_col.dt.hour.fillna(0).astype(int)
        else:
            features['hour'] = 0

        # 2. Mã hóa Label (IP, Method, Path...)
        cols_to_encode = ['ip', 'method', 'path', 'referrer', 'user_agent']
        
        for col in cols_to_encode:
            if col not in features.columns:
                features[col] = "unknown"
            
            features[col] = features[col].astype(str)
            
            # Label Encoding an toàn
            if self.label_encoders and col in self.label_encoders:
                le = self.label_encoders[col]
                features[col + '_enc'] = self.safe_label_transform(le, features[col])
            else:
                features[col + '_enc'] = 0

        # 3. Chuẩn bị Vector đầu vào
        features['status'] = pd.to_numeric(features['status'], errors='coerce').fillna(200)
        features['size'] = pd.to_numeric(features['size'], errors='coerce').fillna(0)

        # Thứ tự cột PHẢI KHỚP 100% với lúc Train
        feature_columns = [
            'ip_enc', 'method_enc', 'path_enc', 'status', 
            'size', 'referrer_enc', 'user_agent_enc', 'hour'
        ]
        
        # Kiểm tra đủ cột chưa
        missing = [c for c in feature_columns if c not in features.columns]
        if missing:
            print(f"❌ Missing columns: {missing}")
            return None, None

        final_data = features[feature_columns].values.astype(np.float32)

        # 4. Scaling
        try:
            X_scaled = self.scaler.transform(final_data)
            return X_scaled, features
        except Exception as e:
            print(f"❌ Scaling Error: {e}")
            return None, None

    def detect_anomalies(self, df: pd.DataFrame):
        threats = []
        if self.model is None:
            return []

        input_data, processed_df = self.preprocess_features(df)
        
        if input_data is None or processed_df is None:
            return []

        try:
            # Predict
            reconstructions = self.model.predict(input_data, verbose=0)
            
            # Tính MSE
            mse = np.mean(np.power(input_data - reconstructions, 2), axis=1)
            
            curr_thresh = self.threshold if self.threshold is not None else 0.05
            # Chỉ lấy index vượt qua ngưỡng nghiêm ngặt này
            anomaly_indices = np.where(mse > curr_thresh)[0]

            print(f"🔍 Scan complete. Threshold={curr_thresh:.4f}. Found {len(anomaly_indices)} anomalies.")
            for idx in anomaly_indices:
                row = processed_df.iloc[idx]
                loss = float(mse[idx])

                # 3. GÁN CỨNG LÀ HIGH (Màu đỏ)
                # Vì đã qua được bộ lọc strict_threshold thì chắc chắn là nguy hiểm
                severity = "High"

                threats.append({
                    "ip": str(row.get('ip', 'Unknown')),
                    "type": "Anomaly Detected",
                    "severity": severity,
                    "time": str(row.get('datetime', '')),
                    "reconstruction_error": round(loss, 4),
                    "details": f"Path: {row.get('path')}"
                })

        except Exception as e:
            print(f"❌ Inference Error: {e}")

        return threats