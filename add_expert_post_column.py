# add_expert_post_column.py
import sqlite3
import os

def add_expert_post_column():
    """Thêm cột expert_post_id vào bảng comments"""
    
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
        
        # Kiểm tra xem cột đã tồn tại chưa
        cursor.execute("PRAGMA table_info(comments)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'expert_post_id' in columns:
            print("✅ Cột 'expert_post_id' đã tồn tại trong bảng comments!")
            return
        
        # Thêm cột expert_post_id
        cursor.execute("""
            ALTER TABLE comments 
            ADD COLUMN expert_post_id INTEGER 
            REFERENCES expert_posts(id)
        """)
        
        # Commit thay đổi
        conn.commit()
        print("✅ Đã thêm cột 'expert_post_id' vào bảng comments thành công!")
        
    except sqlite3.Error as e:
        print(f"❌ Lỗi SQLite: {e}")
    except Exception as e:
        print(f"❌ Lỗi: {e}")
    finally:
        # Đóng kết nối
        if conn:
            conn.close()

if __name__ == "__main__":
    add_expert_post_column()