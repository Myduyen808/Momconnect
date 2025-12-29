# Tạo file create_comment_tables.py
from app import app, db
from models import CommentLike, CommentReport

with app.app_context():
    # Tạo bảng mới
    db.create_all()
    print("✅ Đã tạo bảng comment_likes và comment_reports!")