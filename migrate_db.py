# migrate_db.py - SCRIPT MIGRATION ĐƠN GIẢN CHO WINDOWS

from flask import Flask
from database import db
from models import User, Post, Comment, Follow, Friendship, FriendRequest, Notification, Report, ExpertRequest, Message
from sqlalchemy import text

def migrate_database():
    """Migration đơn giản cho SQLAlchemy 2.0+"""
    
    app = Flask(__name__)
    
    # Cấu hình đơn giản
    app.config['SECRET_KEY'] = 'temp_key'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    with app.app_context():
        try:
            print("🔧 Đang khởi tạo database...")
            
            # Khởi tạo db
            db.init_app(app)
            
            # Tạo tất cả các bảng
            db.create_all()
            
            print("✅ Đã tạo tất cả các bảng thành công!")
            
            # Kiểm tra các bảng quan trọng
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            print(f"\n📋 Danh sách các bảng ({len(tables)}):")
            for table in sorted(tables):
                print(f"   - {table}")
            
            # Kiểm tra bảng quan trọng
            important_tables = ['user', 'friendship', 'friend_request']
            missing = [t for t in important_tables if t not in tables]
            
            if missing:
                print(f"\n❌ Thiếu các bảng: {missing}")
                return False
            else:
                print(f"\n✅ Tất cả bảng quan trọng đã sẵn sàng!")
                
                # Test query
                try:
                    user_count = User.query.count()
                    print(f"📊 Số người dùng: {user_count}")
                    print("✅ Database hoạt động tốt!")
                    return True
                except Exception as e:
                    print(f"❌ Lỗi khi test: {e}")
                    return False
                    
        except Exception as e:
            print(f"❌ Lỗi migration: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    print("🚀 Bắt đầu migration database...")
    success = migrate_database()
    
    if success:
        print("\n🎉 Migration thành công!")
        print("\n📝 Các bước tiếp theo:")
        print("1. Thêm vào app.py: from friendship_routes import *")
        print("2. Thêm vào app.py: from friendship_status_route import *")
        print("3. Xóa routes cũ về kết bạn trong app.py")
        print("4. Khởi động lại ứng dụng Flask")
    else:
        print("\n❌ Migration thất bại!")
        print("Vui lòng kiểm tra lỗi và thử lại.")