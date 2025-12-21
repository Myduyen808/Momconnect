# fix_notification_columns.py - SỬA CÁC CỘT THIẾU CHO BẢNG NOTIFICATIONS

import sqlite3
import os

def fix_notification_columns():
    """Thêm các cột còn thiếu vào bảng notifications"""
    
    db_path = 'db/momconnect.db'
    
    if not os.path.exists(db_path):
        print("❌ Database không tồn tại!")
        return False
    
    try:
        # Kết nối database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔍 Kiểm tra cấu trúc bảng notifications...")
        
        # Kiểm tra các cột hiện có
        cursor.execute("PRAGMA table_info(notifications)")
        columns = [row[1] for row in cursor.fetchall()]
        print(f"Các cột hiện có: {columns}")
        
        # Thêm cột post_id nếu chưa có
        if 'post_id' not in columns:
            print("➕ Thêm cột post_id...")
            cursor.execute("ALTER TABLE notifications ADD COLUMN post_id INTEGER")
            print("✅ Đã thêm cột post_id")
        else:
            print("ℹ️ Cột post_id đã tồn tại")
        
        # Thêm cột comment_id nếu chưa có
        if 'comment_id' not in columns:
            print("➕ Thêm cột comment_id...")
            cursor.execute("ALTER TABLE notifications ADD COLUMN comment_id INTEGER")
            print("✅ Đã thêm cột comment_id")
        else:
            print("ℹ️ Cột comment_id đã tồn tại")
        
        # Xóa cột related_id nếu tồn tại (vì đã có related_user_id)
        if 'related_id' in columns:
            print("🗑️ Xóa cột related_id không cần thiết...")
            cursor.execute("ALTER TABLE notifications DROP COLUMN related_id")
            print("✅ Đã xóa cột related_id")
        
        # Commit changes
        conn.commit()
        conn.close()
        
        print("🎉 Hoàn tất! Cấu trúc bảng notifications đã được cập nhật.")
        return True
        
    except Exception as e:
        print(f"❌ Lỗi khi cập nhật database: {e}")
        return False

if __name__ == '__main__':
    print("🔧 Bắt đầu sửa cấu trúc bảng notifications...")
    success = fix_notification_columns()
    
    if success:
        print("\n📋 Các bước tiếp theo:")
        print("1. Khởi động lại ứng dụng: python app.py")
        print("2. Test chức năng thông báo")
        print("3. Kiểm tra các thông báo được tạo")
    else:
        print("\n❌ Vui lòng kiểm tra lỗi và thử lại")