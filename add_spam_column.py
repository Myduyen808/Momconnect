# add_spam_column.py
from app import app, db
from sqlalchemy import text

with app.app_context():
    try:
        # Thêm cột is_spam vào bảng comments
        with db.engine.connect() as conn:
            conn.execute(text('ALTER TABLE comments ADD COLUMN is_spam BOOLEAN DEFAULT 0'))
            conn.commit()
        print("✅ Đã thêm cột is_spam vào bảng comments!")
    except Exception as e:
        if 'duplicate column name' in str(e).lower():
            print("✅ Cột is_spam đã tồn tại!")
        else:
            print(f"❌ Lỗi: {e}")