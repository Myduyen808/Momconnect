# train_model.py
from app import app, db
from models import Post
from recommendation_system import recommender
import pandas as pd

def train_recommendation_model():
    print("="*60)
    print("🎓 HUẤN LUYỆN MODEL GỢI Ý BÀI VIẾT")
    print("="*60)

    with app.app_context():
        # Lấy tất cả bài viết
        posts = Post.query.all()
        print(f"\n📊 Tổng số bài viết trong database: {len(posts)}")
        
        if len(posts) < 3:
            print("❌ Cần ít nhất 3 bài viết để train model!")
            return False

        # Chuẩn bị dữ liệu
        data = []
        empty_count = 0
        
        for post in posts:
            title = (post.title or '').strip()
            content = (post.content or '').strip()
            
            if not title and not content:
                empty_count += 1
                continue
            
            data.append({
                'id': post.id,
                'title': title,
                'content': content,
                'user_id': post.user_id,
                'category': post.category
            })

        print(f"✅ Có {len(data)} bài viết CÓ NỘI DUNG")
        print(f"⚠️ Bỏ qua {empty_count} bài viết RỖNG")

        if len(data) < 3:
            print(f"❌ Chỉ có {len(data)} bài có nội dung → không đủ để train!")
            return False

        # Tạo DataFrame
        df = pd.DataFrame(data)
        
        # Hiển thị mẫu
        print("\n📄 Mẫu 5 bài đầu tiên:")
        print(df[['id', 'title', 'category']].head())
        
        # Huấn luyện
        print("\n🔄 Đang huấn luyện model...")
        success = recommender.train(df)
        
        if success:
            print("\n" + "="*60)
            print("🎉 HUẤN LUYỆN THÀNH CÔNG!")
            print("="*60)
            print(f"✅ Model đã lưu tại: models/recommendation_model.pkl")
            print(f"✅ Số bài viết trong model: {len(recommender.post_ids)}")
            
            # Test thử
            if len(recommender.post_ids) > 0:
                test_id = recommender.post_ids[0]
                similar = recommender.get_similar_posts(test_id, top_n=3)
                print(f"\n🧪 Test gợi ý cho bài {test_id}: {len(similar)} bài tương tự")
            
            return True
        else:
            print("\n❌ HUẤN LUYỆN THẤT BẠI!")
            return False

if __name__ == "__main__":
    train_recommendation_model()