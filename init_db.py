# init_db.py
from flask import Flask
from database import db, init_app
from models import User, ExpertRequest
from werkzeug.security import generate_password_hash
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
init_app(app)

with app.app_context():
    db.create_all()
    print("Tất cả bảng đã được tạo!")

    # 1. ADMIN
    if not User.query.filter_by(email='admin@momconnect.com').first():
        admin = User(
            name='Admin MomConnect',
            email='admin@momconnect.com',
            password=generate_password_hash('admin123'),
            role='admin'
        )
        db.session.add(admin)
        db.session.commit()
        print("Admin: admin@momconnect.com / admin123")

    # 2. CHUYÊN GIA (đã duyệt)
# 2. CHUYÊN GIA (đã duyệt)
    if not User.query.filter_by(email='expert@momconnect.com').first():
        expert = User(
            name='BS. Lan Anh',
            email='expert@momconnect.com',
            password=generate_password_hash('expert123'),
            role='expert',                      # ← SỬA THÀNH 'expert'
            is_verified_expert=True,            # ← Vẫn giữ để tương thích code cũ
            expert_category='dinh_duong',
            bio='Bác sĩ nhi khoa với 10 năm kinh nghiệm chuyên về dinh dưỡng trẻ em',
            points=5000,                        # ← Đưa điểm cao để test badge
            children_count=2
        )
        db.session.add(expert)
        db.session.commit()
        print("Chuyên gia: expert@momconnect.com / expert123 (role=expert + verified)")

    # 3. USER TEST (để test Postman)
    if not User.query.filter_by(email='test@example.com').first():
        test_user = User(
            name='Mẹ Bé Test',
            email='test@example.com',
            password=generate_password_hash('123456'),
            points=100,
            role='user'
        )
        db.session.add(test_user)
        db.session.commit()
        print("User test: test@example.com / 123456")

    print("HOÀN TẤT! Dùng test@example.com để test Postman.")