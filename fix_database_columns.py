# fix_database_columns.py - SCRIPT SỬA CÁC CỘT THIẾU TRONG DATABASE

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

def fix_database_columns():
    """Sửa các cột thiếu trong database"""
    
    with app.app_context():
        try:
            print("🔧 Đang kiểm tra và sửa cấu trúc database...")
            
            # Kiểm tra và thêm các cột thiếu cho bảng user
            with db.engine.connect() as conn:
                # Lấy cấu trúc bảng user
                result = conn.execute(text('PRAGMA table_info(user)')).fetchall()
                existing_columns = [col[1] for col in result]
                
                print(f"📋 Các cột hiện có trong bảng user: {existing_columns}")
                
                # Thêm các cột thiếu
                columns_to_add = {
                    'children_count': 'INTEGER DEFAULT 0',
                    'children_ages': 'VARCHAR(100)',
                    'points': 'INTEGER DEFAULT 0',
                    'role': 'VARCHAR(20) DEFAULT "user"',
                    'is_active': 'BOOLEAN DEFAULT 1',
                    'is_verified_expert': 'BOOLEAN DEFAULT 0',
                    'expert_request': 'TEXT',
                    'expert_category': 'VARCHAR(50)'
                }
                
                for column_name, column_def in columns_to_add.items():
                    if column_name not in existing_columns:
                        try:
                            print(f"➕ Thêm cột {column_name}...")
                            conn.execute(text(f'ALTER TABLE user ADD COLUMN {column_name} {column_def}'))
                            conn.commit()
                            print(f"✅ Đã thêm cột {column_name}")
                        except Exception as e:
                            print(f"⚠️ Lỗi khi thêm cột {column_name}: {e}")
                    else:
                        print(f"✅ Cột {column_name} đã tồn tại")
                
                # Kiểm tra bảng post
                result = conn.execute(text('PRAGMA table_info(post)')).fetchall()
                post_columns = [col[1] for col in result]
                
                post_columns_to_add = {
                    'category': 'VARCHAR(50) DEFAULT "other"',
                    'is_expert_post': 'BOOLEAN DEFAULT 0',
                    'likes': 'INTEGER DEFAULT 0',
                    'comments_count': 'INTEGER DEFAULT 0',
                    'images': 'TEXT',
                    'video': 'VARCHAR(200)'
                }
                
                print(f"\n📋 Các cột hiện có trong bảng post: {post_columns}")
                
                for column_name, column_def in post_columns_to_add.items():
                    if column_name not in post_columns:
                        try:
                            print(f"➕ Thêm cột {column_name}...")
                            conn.execute(text(f'ALTER TABLE post ADD COLUMN {column_name} {column_def}'))
                            conn.commit()
                            print(f"✅ Đã thêm cột {column_name}")
                        except Exception as e:
                            print(f"⚠️ Lỗi khi thêm cột {column_name}: {e}")
                    else:
                        print(f"✅ Cột {column_name} đã tồn tại")
                
                # Kiểm tra và tạo các bảng thiếu
                tables_to_check = ['comment', 'notification', 'report', 'expert_request', 'message']
                
                result = conn.execute(text('''
                    SELECT name FROM sqlite_master 
                    WHERE type='table'
                ''')).fetchall()
                
                existing_tables = [table[0] for table in result]
                print(f"\n📋 Các bảng hiện có: {existing_tables}")
                
                # Định nghĩa các bảng thiếu
                table_definitions = {
                    'comment': '''
                        CREATE TABLE IF NOT EXISTS comment (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            content TEXT,
                            user_id INTEGER,
                            post_id INTEGER,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (user_id) REFERENCES user (id),
                            FOREIGN KEY (post_id) REFERENCES post (id)
                        )
                    ''',
                    'notification': '''
                        CREATE TABLE IF NOT EXISTS notification (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER NOT NULL,
                            title VARCHAR(100) NOT NULL,
                            message TEXT NOT NULL,
                            type VARCHAR(20),
                            related_id INTEGER,
                            related_user_id INTEGER,
                            is_read BOOLEAN DEFAULT 0,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (user_id) REFERENCES user (id),
                            FOREIGN KEY (related_user_id) REFERENCES user (id)
                        )
                    ''',
                    'report': '''
                        CREATE TABLE IF NOT EXISTS report (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            post_id INTEGER NOT NULL,
                            user_id INTEGER NOT NULL,
                            reason VARCHAR(200) NOT NULL,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (post_id) REFERENCES post (id),
                            FOREIGN KEY (user_id) REFERENCES user (id)
                        )
                    ''',
                    'expert_request': '''
                        CREATE TABLE IF NOT EXISTS expert_request (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER NOT NULL,
                            certificate VARCHAR(200),
                            reason TEXT NOT NULL,
                            status VARCHAR(20) DEFAULT 'pending',
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            admin_note TEXT,
                            FOREIGN KEY (user_id) REFERENCES user (id)
                        )
                    ''',
                    'message': '''
                        CREATE TABLE IF NOT EXISTS message (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            sender_id INTEGER NOT NULL,
                            receiver_id INTEGER NOT NULL,
                            content TEXT NOT NULL,
                            type VARCHAR(20) DEFAULT 'text',
                            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                            is_read BOOLEAN DEFAULT 0,
                            FOREIGN KEY (sender_id) REFERENCES user (id),
                            FOREIGN KEY (receiver_id) REFERENCES user (id)
                        )
                    '''
                }
                
                for table_name, table_def in table_definitions.items():
                    if table_name not in existing_tables:
                        try:
                            print(f"➕ Tạo bảng {table_name}...")
                            conn.execute(text(table_def))
                            conn.commit()
                            print(f"✅ Đã tạo bảng {table_name}")
                        except Exception as e:
                            print(f"⚠️ Lỗi khi tạo bảng {table_name}: {e}")
                    else:
                        print(f"✅ Bảng {table_name} đã tồn tại")
            
            print("\n🎉 Hoàn tất sửa database!")
            return True
            
        except Exception as e:
            print(f"❌ Lỗi khi sửa database: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    print("🚀 Bắt đầu sửa database...")
    success = fix_database_columns()
    
    if success:
        print("\n✅ Database đã sẵn sàng!")
        print("\n📝 Các bước tiếp theo:")
        print("1. Chạy lại: python app.py")
        print("2. Test các chức năng")
    else:
        print("\n❌ Vui lòng kiểm tra lỗi và thử lại")