# update_badges.py
import sqlite3
import os

# Đường dẫn database
db_path = 'instance/database.db'

# Kiểm tra file tồn tại
if not os.path.exists(db_path):
    print(f"❌ Không tìm thấy database tại: {db_path}")
    exit(1)

print(f"📁 Đang kết nối database: {db_path}")

# Kết nối database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Cập nhật badge cho người dùng chưa có
print("🔧 Đang cập nhật badge cho người dùng chưa có...")

try:
    # Đặt badge mặc định cho người dùng chưa có
    cursor.execute("""
        UPDATE users 
        SET badge = 'Mầm Non 👶' 
        WHERE badge IS NULL OR badge = ''
    """)
    
    # Đặt các giá trị mặc định khác nếu cần
    cursor.execute("""
        UPDATE users 
        SET specialty = 'Chưa xác định' 
        WHERE specialty IS NULL OR specialty = ''
    """)
    
    cursor.execute("""
        UPDATE users 
        SET experience_years = 0 
        WHERE experience_years IS NULL
    """)
    
    cursor.execute("""
        UPDATE users 
        SET workplace = 'Chưa xác định' 
        WHERE workplace IS NULL OR workplace = ''
    """)
    
    cursor.execute("""
        UPDATE users 
        SET credibility_score = 0 
        WHERE credibility_score IS NULL
    """)
    
    # Lưu thay đổi
    conn.commit()
    
    # Hiển thị số lượng người dùng đã cập nhật
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE badge = 'Mầm Non 👶'")
    updated_users = cursor.fetchone()[0]
    
    print(f"✅ Đã cập nhật badge cho {updated_users}/{total_users} người dùng")
    print("✅ Đã cập nhật các giá trị mặc định khác")
    
except sqlite3.Error as e:
    print(f"❌ Lỗi khi cập nhật: {e}")
    conn.rollback()
finally:
    conn.close()

print(f"\n💡 Bây giờ bạn có thể chạy: python app.py")