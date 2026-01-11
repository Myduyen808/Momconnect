# add_expert_posts_table.py
import sqlite3
import os

def create_expert_posts_table():
    """Tạo bảng expert_posts nếu chưa tồn tại"""
    
    # Đường dẫn đến file database
    db_file = 'instance/database.db'
    
    if not os.path.exists(db_file):
        print(f"❌ File database '{db_file}' không tồn tại!")
        print("Vui lòng kiểm tra lại đường dẫn đến file database của bạn.")
        return
    
    try:
        # Kết nối đến database
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # Kiểm tra xem bảng đã tồn tại chưa
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='expert_posts'
        """)
        
        if cursor.fetchone():
            print("✅ Bảng 'expert_posts' đã tồn tại!")
            return
        
        # Tạo bảng expert_posts
        cursor.execute("""
            CREATE TABLE expert_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                expert_id INTEGER NOT NULL,
                title VARCHAR(200) NOT NULL,
                content TEXT NOT NULL,
                category VARCHAR(50),
                medical_references TEXT,
                views_count INTEGER DEFAULT 0,
                likes_count INTEGER DEFAULT 0,
                comments_count INTEGER DEFAULT 0,
                is_published BOOLEAN DEFAULT 0,
                published_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (expert_id) REFERENCES expert_profiles (id)
            )
        """)
        
        # Commit thay đổi
        conn.commit()
        print("✅ Đã tạo bảng 'expert_posts' thành công!")
        
    except sqlite3.Error as e:
        print(f"❌ Lỗi SQLite: {e}")
    except Exception as e:
        print(f"❌ Lỗi: {e}")
    finally:
        # Đóng kết nối
        if conn:
            conn.close()

if __name__ == "__main__":
    create_expert_posts_table()