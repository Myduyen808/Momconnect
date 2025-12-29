import sqlite3
import os

# Đường dẫn đến database
db_path = 'instance/database.db'

if not os.path.exists(db_path):
    print(f"❌ Không tìm thấy database tại {db_path}")
    exit(1)

# Kết nối database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # Kiểm tra xem cột is_spam đã tồn tại chưa
    cursor.execute("PRAGMA table_info(comments)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'is_spam' in columns:
        print("✅ Cột is_spam đã tồn tại!")
    else:
        # Thêm cột is_spam
        cursor.execute("ALTER TABLE comments ADD COLUMN is_spam BOOLEAN DEFAULT 0")
        conn.commit()
        print("✅ Đã thêm cột is_spam vào bảng comments!")
    
    # Cập nhật giá trị mặc định cho các comment cũ
    cursor.execute("UPDATE comments SET is_spam = 0 WHERE is_spam IS NULL")
    conn.commit()
    print("✅ Đã cập nhật giá trị mặc định!")
    
except Exception as e:
    print(f"❌ Lỗi: {e}")
    conn.rollback()
finally:
    conn.close()

print("\n🎉 Hoàn tất! Bạn có thể chạy app bây giờ.")