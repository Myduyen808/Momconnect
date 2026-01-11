# add_columns.py
import sqlite3
import os

# Đường dẫn database
db_path = 'instance/database.db'

# Kiểm tra file tồn tại
if not os.path.exists(db_path):
    print(f"❌ Không tìm thấy database tại: {db_path}")
    print("Vui lòng kiểm tra lại đường dẫn!")
    exit(1)

print(f"📁 Đang kết nối database: {db_path}")

# Kết nối database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Kiểm tra bảng users có tồn tại không
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
if not cursor.fetchone():
    print("❌ Bảng 'users' không tồn tại!")
    print("Bạn cần tạo database trước!")
    conn.close()
    exit(1)

print("✅ Bảng 'users' đã tồn tại")

# Lấy danh sách cột hiện tại
cursor.execute("PRAGMA table_info(users)")
existing_columns = [row[1] for row in cursor.fetchall()]
print(f"\n📋 Các cột hiện có: {', '.join(existing_columns)}")

# Danh sách các cột cần thêm
columns_to_add = [
    ("badge", "TEXT"),
    ("specialty", "TEXT"),
    ("experience_years", "INTEGER"),
    ("workplace", "TEXT"),
    ("license_number", "TEXT"),
    ("license_expiry", "DATE"),
    ("consultation_fee", "REAL"),
    ("education", "TEXT"),
    ("certifications", "TEXT"),
    ("availability", "TEXT DEFAULT 'available'"),
    ("credibility_score", "REAL DEFAULT 0")
]

print(f"\n🔧 Bắt đầu thêm {len(columns_to_add)} cột...\n")

added_count = 0
skipped_count = 0

# Thêm từng cột
for column_name, column_type in columns_to_add:
    # Kiểm tra cột đã tồn tại chưa
    if column_name in existing_columns:
        print(f"⚠️  Cột '{column_name}' đã tồn tại - Bỏ qua")
        skipped_count += 1
        continue
    
    # Thêm cột mới
    sql = f"ALTER TABLE users ADD COLUMN {column_name} {column_type}"
    try:
        cursor.execute(sql)
        print(f"✅ Đã thêm cột: {column_name} ({column_type})")
        added_count += 1
    except sqlite3.OperationalError as e:
        print(f"❌ Lỗi khi thêm cột '{column_name}': {e}")

# Lưu thay đổi
conn.commit()
conn.close()

# Tổng kết
print(f"\n{'='*60}")
print(f"🎉 HOÀN THÀNH!")
print(f"{'='*60}")
print(f"✅ Đã thêm mới: {added_count} cột")
print(f"⚠️  Đã bỏ qua: {skipped_count} cột (đã tồn tại)")
print(f"📊 Tổng cộng: {added_count + skipped_count} cột")
print(f"\n💡 Bây giờ bạn có thể chạy: python app.py")