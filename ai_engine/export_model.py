import pandas as pd
import pickle
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def main():
    print("🚀 Bắt đầu quá trình huấn luyện và đóng gói mô hình...")

    # 1. Khai báo đường dẫn tương đối (vì file này đang nằm trong thư mục ai_engine/)
    input_file = '../data/processed/movies_cleaned_soup.csv'
    model_dir = '../data/models/'
    
    # Đảm bảo thư mục chứa model đã tồn tại, nếu chưa thì tự động tạo
    os.makedirs(model_dir, exist_ok=True)

    # 2. Đọc dữ liệu
    print(f"📂 Đang đọc dữ liệu sạch từ {input_file}...")
    try:
        df = pd.read_csv(input_file)
        # Phòng thủ lỗi Pandas tự chuyển chuỗi rỗng thành NaN
        df['soup'] = df['soup'].fillna('') 
    except FileNotFoundError:
        print(f"❌ Lỗi: Không tìm thấy file {input_file}. Hãy kiểm tra lại đường dẫn!")
        return

    # 3. Vector hóa văn bản bằng TF-IDF
    print("⚙️ Đang Vector hóa văn bản (TF-IDF) với tối đa 5000 features...")
    tfidf = TfidfVectorizer(stop_words='english', max_features=5000)
    tfidf_matrix = tfidf.fit_transform(df['soup'])

    # 4. Tính toán Ma trận tương đồng (Cosine Similarity)
    print("📐 Đang tính toán Ma trận Cosine Similarity...")
    cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)

    # 5. Chuẩn bị dữ liệu cho Backend
    print("📦 Đang đóng gói dữ liệu...")
    # Chỉ trích xuất các cột Backend thực sự cần để giao diện Web hiển thị
    movies_export = df[['movieId', 'tmdbId', 'title', 'poster_path']].copy()
    
    # Chuyển Dataframe thành dạng danh sách các Dictionary (Rất tối ưu cho API trả về JSON)
    movie_dict = movies_export.to_dict(orient='records')

    # 6. Xuất ra file .pkl vào đúng thư mục data/models/
    dict_path = os.path.join(model_dir, 'movie_dict.pkl')
    sim_path = os.path.join(model_dir, 'similarity.pkl')

    pickle.dump(movie_dict, open(dict_path, 'wb'))
    pickle.dump(cosine_sim, open(sim_path, 'wb'))

    print(f"🎉 HOÀN TẤT! Các file đã được lưu an toàn tại:")
    print(f"   - {dict_path}")
    print(f"   - {sim_path}")

if __name__ == "__main__":
    main()