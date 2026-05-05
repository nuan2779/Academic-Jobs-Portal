import pandas as pd
import numpy as np
import faiss
import os
import torch
import pickle
import mysql.connector
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

# --- 1. CẤU HÌNH HỆ THỐNG ---[cite: 1, 3]
DB_CONFIG = {
    'user': 'root',
    'password': 'Luan270706', # Thay bằng mật khẩu MySQL của Luân
    'host': '127.0.0.1',
    'database': 'academic_jobs_portal',
    'auth_plugin': 'mysql_native_password'
}

# Đường dẫn lưu trữ output
OUTPUT_DIR = r'C:/Users/Admin/Downloads/AcademicGateDAta/cleaned_for_sql'
MODEL_NAME = 'BAAI/bge-small-en-v1.5'
BATCH_SIZE = 64 # Tận dụng VRAM GPU của Luân

# Kiểm tra thiết bị xử lý
device = 'cuda' if torch.cuda.is_available() else 'cpu'
print(f"🖥️  Device: {device.upper()}")

# --- 2. KẾT NỐI VÀ LẤY DỮ LIỆU ---[cite: 1, 3, 5]
def fetch_all_data():
    try:
        print("🔌 Đang kết nối tới MySQL...")
        conn = mysql.connector.connect(**DB_CONFIG)
        
        # Lấy hết data (bao gồm cả Inactive) để làm giàu kho tri thức
        query = """
            SELECT JobID, JobTitle, JobDescription, Country, CategoryID, Status 
            FROM AcademicJobs
        """
        df = pd.read_sql(query, conn)
        conn.close()
        print(f"✅ Đã tải {len(df):,} bản ghi từ database.")
        return df
    except Exception as e:
        print(f"❌ Lỗi kết nối DB: {e}")
        return None

# --- 3. QUY TRÌNH XỬ LÝ VECTOR (ENCODING & POOLING) ---[cite: 1, 4]
def process_embeddings(df):
    model = SentenceTransformer(MODEL_NAME, device=device)
    all_embeddings = []
    metadata = []
    
    print(f"🚀 Bắt đầu quá trình Vectorization (Batch Size: {BATCH_SIZE})...")
    
    for _, row in tqdm(df.iterrows(), total=len(df), desc="Processing Jobs"):
        # Kết hợp Title và mô tả chi tiết (từ cột NonHTML đã nạp)
        combined_text = f"Job Title: {row['JobTitle']}. Description: {row['JobDescription']}"
        
        # Bước 1: Chunking (1500 ký tự, Overlap 200 -> Step 1300)
        chunks = [combined_text[i:i+1500] for i in range(0, len(combined_text), 1300)]
        
        # Bước 2: Encoding các chunk[cite: 4]
        chunk_vecs = model.encode(chunks, batch_size=BATCH_SIZE, show_progress_bar=False)
        
        # Bước 3: Mean Pooling - Lấy trung bình cộng để ra vector đại diện duy nhất[cite: 4]
        # Công thức: V_final = (v1 + v2 + ... + vn) / n
        job_vector = np.mean(chunk_vecs, axis=0)
        
        all_embeddings.append(job_vector)
        
        # Lưu Metadata phục vụ cho Hybrid Search Filter[cite: 1, 3]
        metadata.append({
            'job_id': row['JobID'],
            'country': row['Country'],
            'category_id': row['CategoryID'],
            'status': row['Status']
        })
        
    return np.array(all_embeddings).astype('float32'), metadata

# --- 4. CHẠY PIPELINE ---[cite: 1, 4]
if __name__ == "__main__":
    df_jobs = fetch_all_data()
    
    if df_jobs is not None:
        # Xử lý vector
        embeddings, meta = process_embeddings(df_jobs.fillna(""))
        
        # Lưu trữ file thô
        np.save(os.path.join(OUTPUT_DIR, 'embeddings.npy'), embeddings)
        with open(os.path.join(OUTPUT_DIR, 'metadata.pkl'), 'wb') as f:
            pickle.dump(meta, f)
        
        # Bước 5: Xây dựng HNSW Index (Vũ khí lõi của tìm kiếm ngữ nghĩa)[cite: 4]
        print("🏗️  Đang xây dựng đồ thị HNSW Index...")
        dim = embeddings.shape[1]
        
        # Tham số M=32 cho độ kết nối tốt
        index = faiss.IndexHNSWFlat(dim, 32)
        
        # Các tham số tối ưu Luân đã chọn để cân bằng Tốc độ/Chính xác[cite: 4]
        index.hnsw.efConstruction = 200 # Lúc xây dựng đồ thị
        index.hnsw.efSearch = 128       # Lúc truy vấn thực tế
        
        index.add(embeddings)
        
        # Xuất file index cuối cùng
        faiss.write_index(index, os.path.join(OUTPUT_DIR, 'hnsw_index.bin'))
        
        print(f"\n🎉 HOÀN THÀNH!")
        print(f"📍 Files đã lưu tại: {OUTPUT_DIR}")
        print(f"📊 Tổng số Vector: {len(embeddings)}")