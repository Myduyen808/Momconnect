# fix_time_slots_columns.py - Thêm các cột thiếu vào bảng time_slots (an toàn, không mất dữ liệu)

import sqlite3
import os

# Đường dẫn database của em (đổi nếu tên file khác)
DB_PATH = os.path.join('instance', 'database.db')  # hoặc 'momconnect.db' nếu tên khác

def add_missing_columns():
    if not os.path.exists(DB_PATH):
        print(f"❌ Không tìm thấy database tại: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Lấy danh sách cột hiện có trong bảng time_slots
        cursor.execute("PRAGMA table_info(time_slots)")
        existing_columns = {col[1] for col in cursor.fetchall()}  # col[1] là tên cột

        print("Cột hiện có trong time_slots:", existing_columns)

        # Các cột cần thêm (theo model của em)
        needed_columns = {
            'notes': 'TEXT',           # hoặc 'note' nếu em đặt tên là note
            'max_participants': 'INTEGER DEFAULT 1'
            # Thêm cột khác nếu cần, ví dụ:
            # 'duration_minutes': 'INTEGER DEFAULT 30'
        }

        added = []
        for col_name, col_type in needed_columns.items():
            if col_name not in existing_columns:
                print(f"Đang thêm cột '{col_name}' ({col_type})...")
                cursor.execute(f"ALTER TABLE time_slots ADD COLUMN {col_name} {col_type}")
                added.append(col_name)
            else:
                print(f"✅ Cột '{col_name}' đã tồn tại, bỏ qua.")

        if added:
            conn.commit()
            print(f"🎉 Đã thêm thành công các cột: {', '.join(added)}")
        else:
            print("Tất cả cột cần thiết đã tồn tại. Không cần thêm gì.")

    except sqlite3.OperationalError as e:
        print(f"Lỗi: {e}")
        print("Có thể bảng 'time_slots' chưa tồn tại hoặc database bị lỗi. Hãy kiểm tra lại.")
    finally:
        conn.close()

if __name__ == "__main__":
    print("=== SCRIPT SỬA BẢNG TIME_SLOTS (THÊM CỘT THIẾU) ===")
    print(f"Database: {os.path.abspath(DB_PATH)}")
    add_missing_columns()
    print("Hoàn tất! Chạy lại app.py để kiểm tra.")