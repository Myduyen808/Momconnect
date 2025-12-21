# create_tables.py - SCRIPT TẠO BẢNG ĐƠN GIẢN NHẤT

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

# Tạo app đơn giản
app = Flask(__name__)
app.config['SECRET_KEY'] = 'temp_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Định nghĩa các bảng quan trọng
class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))
    avatar = db.Column(db.String(200))
    bio = db.Column(db.Text)
    points = db.Column(db.Integer, default=0)
    role = db.Column(db.String(20), default='user')
    is_active = db.Column(db.Boolean, default=True)
    is_verified_expert = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

class Friendship(db.Model):
    __tablename__ = 'friendship'
    id = db.Column(db.Integer, primary_key=True)
    user1_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user2_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    
    __table_args__ = (db.UniqueConstraint('user1_id', 'user2_id'),)

class FriendRequest(db.Model):
    __tablename__ = 'friend_request'
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now())
    
    __table_args__ = (db.UniqueConstraint('sender_id', 'receiver_id'),)

class Post(db.Model):
    __tablename__ = 'post'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

def create_all_tables():
    """Tạo tất cả các bảng"""
    
    with app.app_context():
        try:
            print("🚀 Đang tạo bảng...")
            
            # Xóa bảng cũ nếu có conflict
            try:
                db.drop_all()
                print("🗑️ Đã xóa các bảng cũ")
            except:
                pass
            
            # Tạo lại tất cả
            db.create_all()
            print("✅ Đã tạo tất cả các bảng mới!")
            
            # Kiểm tra
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            print(f"\n📋 Các bảng đã tạo ({len(tables)}):")
            for table in sorted(tables):
                print(f"   - {table}")
            
            # Test thêm user mẫu
            try:
                test_user = User(
                    name='Test User',
                    email='test@example.com',
                    password='hashed_password'
                )
                db.session.add(test_user)
                db.session.commit()
                print(f"\n✅ Test query thành công! Đã thêm user ID: {test_user.id}")
                
                # Xóa user test
                db.session.delete(test_user)
                db.session.commit()
                print("✅ Đã xóa user test")
                
            except Exception as e:
                print(f"❌ Lỗi test query: {e}")
                return False
            
            print("\n🎉 Database sẵn sàng sử dụng!")
            return True
            
        except Exception as e:
            print(f"❌ Lỗi khi tạo bảng: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    print("🔧 Bắt đầu tạo database...")
    success = create_all_tables()
    
    if success:
        print("\n📝 Các bước tiếp theo:")
        print("1. Copy các file models.py, friendship_routes.py vào project")
        print("2. Import routes vào app.py")
        print("3. Khởi động lại ứng dụng")
    else:
        print("\n❌ Vui lòng kiểm tra lỗi và thử lại")