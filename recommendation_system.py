# recommendation_system.py
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pickle
import os
import re

class PostRecommender:
    def __init__(self, model_path='models/recommendation_model.pkl'):
        self.vectorizer = None
        self.tfidf_matrix = None
        self.post_ids = []
        self.post_data = None
        self.model_path = model_path
        self.load_model()

    def preprocess_text(self, text):
        """Tiền xử lý tiếng Việt: loại bỏ ký tự đặc biệt, chuyển thường, giữ từ ghép"""
        if not text or not isinstance(text, str):
            return ""
        # Loại bỏ ký tự đặc biệt nhưng giữ dấu cách
        text = re.sub(r'[^\w\sàáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđ]', '', text.lower())
        # Thay nhiều khoảng trắng bằng một
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def train(self, posts_df):
        """Huấn luyện model từ DataFrame posts"""
        print("🚀 Bắt đầu huấn luyện model gợi ý...")

        if 'title' not in posts_df.columns or 'content' not in posts_df.columns:
            print("❌ DataFrame thiếu cột 'title' hoặc 'content'!")
            return False

        # Kết hợp title + content
        posts_df['full_text'] = (posts_df['title'].fillna('') + " " + posts_df['content'].fillna('')).str.strip()
        posts_df['processed'] = posts_df['full_text'].apply(self.preprocess_text)

        # Loại bỏ bài rỗng
        posts_df = posts_df[posts_df['processed'].str.strip() != ''].copy()

        if len(posts_df) < 3:
            print(f"⚠️ Chỉ có {len(posts_df)} bài viết có nội dung → không đủ để train!")
            return False

        self.post_ids = posts_df['id'].tolist()
        self.post_data = posts_df[['id', 'title', 'content', 'user_id']].to_dict('records')

        # TF-IDF với bigram → nhận diện "lật ngửa", "vận động thô", "ăn dặm", "sốt cao"...
        self.vectorizer = TfidfVectorizer(
            max_features=8000,
            ngram_range=(1, 2),           # 1-2 gram rất quan trọng cho tiếng Việt
            min_df=1,                     # Cho phép từ hiếm (vì dữ liệu mẹ bỉm thường ít)
            token_pattern=r'(?u)\b\w+\b'  # Giữ nguyên từ tiếng Việt
        )

        print(f"Vectorizing {len(posts_df)} documents...")
        self.tfidf_matrix = self.vectorizer.fit_transform(posts_df['processed'])

        self.save_model()
        print(f"✅ Huấn luyện thành công! {len(self.post_ids)} bài viết đã được vector hóa.")
        print(f"Từ vựng mẫu: {list(self.vectorizer.vocabulary_.keys())[:10]}...")
        return True

    def save_model(self):
        if not os.path.exists(os.path.dirname(self.model_path)):
            os.makedirs(os.path.dirname(self.model_path))
        with open(self.model_path, 'wb') as f:
            pickle.dump({
                'vectorizer': self.vectorizer,
                'tfidf_matrix': self.tfidf_matrix,
                'post_ids': self.post_ids,
                'post_data': self.post_data
            }, f)
        print(f"💾 Model đã được lưu tại: {self.model_path}")

    def load_model(self):
        if os.path.exists(self.model_path):
            with open(self.model_path, 'rb') as f:
                data = pickle.load(f)
                self.vectorizer = data.get('vectorizer')
                self.tfidf_matrix = data.get('tfidf_matrix')
                self.post_ids = data.get('post_ids', [])
                self.post_data = data.get('post_data', None)
            print(f"✅ Model đã load thành công ({len(self.post_ids)} bài viết)")
        else:
            print("⚠️ Chưa có model, cần huấn luyện trước!")

    def get_similar_posts(self, post_id, top_n=5):
        if self.tfidf_matrix is None or not self.post_ids:
            print("Model chưa được load hoặc chưa huấn luyện!")
            return []

        if post_id not in self.post_ids:
            print(f"⚠️ Post ID {post_id} không có trong model!")
            return []

        try:
            idx = self.post_ids.index(post_id)
            sim_scores = cosine_similarity(self.tfidf_matrix[idx], self.tfidf_matrix).flatten()
            sim_scores[idx] = 0  # Loại bỏ chính nó

            top_indices = sim_scores.argsort()[-top_n:][::-1]
            results = []
            for i in top_indices:
                results.append((self.post_ids[i], float(sim_scores[i])))
            return results
        except Exception as e:
            print(f"Lỗi khi tính similarity: {e}")
            return []

    def recommend_for_user(self, liked_post_ids, top_n=5):
        if self.tfidf_matrix is None or not self.post_ids:
            return []

        valid_liked = [pid for pid in liked_post_ids if pid in self.post_ids]
        if not valid_liked:
            return []

        try:
            liked_indices = [self.post_ids.index(pid) for pid in valid_liked]
            user_vector = self.tfidf_matrix[liked_indices].mean(axis=0)
            sim_scores = cosine_similarity(user_vector, self.tfidf_matrix).flatten()

            # Loại bỏ các bài đã like
            for idx in liked_indices:
                sim_scores[idx] = 0

            top_indices = sim_scores.argsort()[-top_n:][::-1]
            return [self.post_ids[i] for i in top_indices]
        except Exception as e:
            print(f"Lỗi recommend_for_user: {e}")
            return []


# Khởi tạo recommender toàn cục
recommender = PostRecommender()