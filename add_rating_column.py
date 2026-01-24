# add_rating_column.py
import sqlite3
import os

# Đường dẫn database
db_path = 'instance/database.db'

# Kiểm tra database tồn tại
if not os.path.exists(db_path):
    print(f"❌ Không tìm thấy database tại: {db_path}")
    exit(1)

print(f"📁 Đang kết nối database: {db_path}")

# Kết nối database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # Kiểm tra cột rating đã tồn tại chưa
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]

    if "rating" in columns:
        print("ℹ️ Cột 'rating' đã tồn tại, không cần thêm.")
    else:
        print("🔧 Đang thêm cột 'rating' vào bảng users...")

        cursor.execute("""
            ALTER TABLE users
            ADD COLUMN rating REAL DEFAULT 0
        """)

        conn.commit()
        print("✅ Đã thêm cột 'rating' thành công!")

except sqlite3.Error as e:
    print(f"❌ Lỗi khi cập nhật database: {e}")
    conn.rollback()

finally:
    conn.close()

print("\n💡 Xong! Bạn có thể chạy lại app bình thường.")
