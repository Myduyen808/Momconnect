# fix_migration.py - SỬA LỖI MIGRATION

from flask import Flask
from database import db
from models import User, Post, Comment, Follow, Friendship, FriendRequest, Notification, Report, ExpertRequest, Message
from sqlalchemy import text

def fix_database():
    """Sửa lỗi database và tạo các bảng cần thiết"""
    
    app = Flask(__name__)
    app.config.from_object('config.Config')
    
    with app.app_context():
        db.init_app(app)
        
        print("🔧 Bắt đầu sửa database...")
        
        # Xóa các bảng cũ nếu có conflict
        try:
            with db.engine.connect() as conn:
                # Kiểm tra và xóa bảng friend_request cũ nếu không có cột status
                result = conn.execute(text('''
                    PRAGMA table_info(friend_request)
                ''')).fetchall()
                
                has_status = any(col[1] == 'status' for col in result)
                
                if not has_status and result:
                    print("🗑️ Xóa bảng friend_request cũ để tạo lại...")
                    conn.execute(text('DROP TABLE friend_request'))
                    conn.commit()
                    
        except Exception as e:
            print(f"⚠️ Không cần xóa bảng cũ: {e}")
        
        # Tạo tất cả các bảng từ models
        print("📝 Tạo tất cả các bảng từ models...")
        db.create_all()
        
        # Kiểm tra lại
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        
        print(f"\n✅ Hoàn tất! Tổng số bảng: {len(tables)}")
        print("\n📋 Các bảng đã được tạo:")
        for table in sorted(tables):
            print(f"   - {table}")
        
        # Kiểm tra các bảng quan trọng
        key_tables = ['user', 'friendship', 'friend_request']
        missing = [t for t in key_tables if t not in tables]
        
        if missing:
            print(f"\n❌ Thiếu các bảng: {missing}")
            return False
        else:
            print(f"\n✅ Tất cả các bảng quan trọng đã sẵn sàng!")
            
            # Test query
            try:
                user_count = User.query.count()
                print(f"📊 Test query - Số người dùng: {user_count}")
                print("✅ Database hoạt động tốt!")
                return True
            except Exception as e:
                print(f"❌ Lỗi khi test query: {e}")
                return False

if __name__ == '__main__':
    success = fix_database()
    if success:
        print("\n🎉 Database đã sẵn sàng cho hệ thống kết bạn!")
    else:
        print("\n❌ Cần kiểm tra lại cấu hình database!")