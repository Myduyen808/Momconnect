# add_expert_profiles_table.py
import sqlite3
import os

def create_expert_profiles_table():
    """Tạo bảng expert_profiles nếu chưa tồn tại"""
    
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
            WHERE type='table' AND name='expert_profiles'
        """)
        
        if cursor.fetchone():
            print("✅ Bảng 'expert_profiles' đã tồn tại!")
            return
        
        # Tạo bảng expert_profiles
        cursor.execute("""
            CREATE TABLE expert_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                specialty VARCHAR(100) NOT NULL,
                license_number VARCHAR(100),
                license_expiry DATE,
                workplace VARCHAR(200),
                experience_years INTEGER,
                education TEXT,
                certifications TEXT,
                availability VARCHAR(100) DEFAULT 'available',
                consultation_fee FLOAT,
                credibility_score FLOAT DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        # Commit thay đổi
        conn.commit()
        print("✅ Đã tạo bảng 'expert_profiles' thành công!")
        
    except sqlite3.Error as e:
        print(f"❌ Lỗi SQLite: {e}")
    except Exception as e:
        print(f"❌ Lỗi: {e}")
    finally:
        # Đóng kết nối
        if conn:
            conn.close()

if __name__ == "__main__":
    create_expert_profiles_table()