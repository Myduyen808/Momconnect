# check_database.py
import sqlite3
import os

def check_database():
    """Kiểm tra cấu trúc database"""
    
    db_file = 'instance/database.db'
    
    if not os.path.exists(db_file):
        print(f"❌ File database '{db_file}' không tồn tại!")
        return
    
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # Kiểm tra tất cả các bảng
        print("=== Tất cả các bảng trong database ===")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        for table in tables:
            print(f"- {table[0]}")
        
        # Kiểm tra cấu trúc bảng comments
        print("\n=== Cấu trúc bảng comments ===")
        cursor.execute("PRAGMA table_info(comments)")
        columns = cursor.fetchall()
        
        has_expert_post_id = False
        for column in columns:
            print(f"Column: {column[1]}, Type: {column[2]}, NotNull: {column[3]}, Default: {column[4]}")
            if column[1] == 'expert_post_id':
                has_expert_post_id = True
        
        if not has_expert_post_id:
            print("\n⚠️  Cột 'expert_post_id' KHÔNG tồn tại trong bảng comments!")
            print("Bạn cần chạy lại script add_expert_post_column.py")
        else:
            print("\n✅ Cột 'expert_post_id' đã tồn tại trong bảng comments")
        
        # Kiểm tra bảng expert_posts
        print("\n=== Cấu trúc bảng expert_posts ===")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='expert_posts'")
        if cursor.fetchone():
            cursor.execute("PRAGMA table_info(expert_posts)")
            columns = cursor.fetchall()
            for column in columns:
                print(f"Column: {column[1]}, Type: {column[2]}")
        else:
            print("❌ Bảng 'expert_posts' không tồn tại!")
        
    except Exception as e:
        print(f"❌ Lỗi: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    check_database()