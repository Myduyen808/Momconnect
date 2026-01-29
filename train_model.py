# train_model.py
from app import app, db
from models import Post
from recommendation_system import recommender
import pandas as pd

def train_recommendation_model():
    print("="*60)
    print("🎓 BẮT ĐẦU HUẤN LUYỆN MODEL GỢI Ý DỰA TRÊN NỘI DUNG")
    print("="*60)

    with app.app_context():
        posts = Post.query.all()
        if not posts:
            print("❌ Database chưa có bài viết nào!")
            return

        data = []
        for post in posts:
            if not post.title and not post.content:
                continue
            data.append({
                'id': post.id,
                'title': post.title or '',
                'content': post.content or '',
                'user_id': post.user_id
            })

        if len(data) < 3:
            print(f"⚠️ Chỉ có {len(data)} bài viết có nội dung → chưa đủ để train!")
            return

        df = pd.DataFrame(data)
        print(f"✅ Thu thập được {len(df)} bài viết để train")

        success = recommender.train(df)
        if success:
            print("🎉 Huấn luyện hoàn tất! Model đã sẵn sàng gợi ý theo nội dung.")
        else:
            print("❌ Huấn luyện thất bại!")

if __name__ == "__main__":
    train_recommendation_model()