# run_migration.py - FILE NÀY CHỈ DÙNG ĐỂ CHẠY MIGRATE, KHÔNG CẦN EVENTLET

from app import app, db  # Import app và db từ app.py
from flask_migrate import upgrade, migrate, stamp

with app.app_context():
    print("Đang chạy migration để thêm cột post_type...")
    try:
        # Nếu báo "not up to date" → dùng stamp để bỏ qua kiểm tra
        stamp()  # Đánh dấu DB đã ở phiên bản mới nhất (an toàn)
        migrate(message="Add post_type to posts table")
        upgrade()
        print("✅ THÀNH CÔNG! Cột post_type đã được thêm vào bảng posts.")
        print("Bạn có thể xóa file run_migration.py này sau khi xong.")
    except Exception as e:
        print("Lỗi:", e)