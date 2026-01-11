# fix_relationship.py
import sqlite3
import os

def check_table_structure():
    """Kiểm tra cấu trúc bảng để đảm bảo các cột FK đã được tạo đúng"""
    
    # Đường dẫn đến file database
    db_file = 'instance/database.db'
    
    if not os.path.exists(db_file):
        print(f"❌ File database '{db_file}' không tồn tại!")
        return
    
    try:
        # Kết nối đến database
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # Kiểm tra cấu trúc bảng comments
        print("=== Cấu trúc bảng comments ===")
        cursor.execute("PRAGMA table_info(comments)")
        columns = cursor.fetchall()
        for column in columns:
            print(f"{column[1]} - {column[2]}")
        
        # Kiểm tra cấu trúc bảng expert_posts
        print("\n=== Cấu trúc bảng expert_posts ===")
        cursor.execute("PRAGMA table_info(expert_posts)")
        columns = cursor.fetchall()
        for column in columns:
            print(f"{column[1]} - {column[2]}")
        
        # Kiểm tra các khóa ngoại
        print("\n=== Khóa ngoại của bảng comments ===")
        cursor.execute("PRAGMA foreign_key_list(comments)")
        fks = cursor.fetchall()
        for fk in fks:
            print(f"Column: {fk[3]} -> References: {fk[2]}.{fk[4]}")
        
    except sqlite3.Error as e:
        print(f"❌ Lỗi SQLite: {e}")
    except Exception as e:
        print(f"❌ Lỗi: {e}")
    finally:
        # Đóng kết nối
        if conn:
            conn.close()

if __name__ == "__main__":
    check_table_structure()