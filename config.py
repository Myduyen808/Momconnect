import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = 'momconnect_secret_2025'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///database.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(basedir, 'static', 'uploads')
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    
    # === THÊM MỚI: CẤU HÌNH MÚI GIỜ ===
    # Thiết lập múi giờ mặc định cho ứng dụng là Việt Nam (UTC+7)
    TIMEZONE = 'Asia/Ho_Chi_Minh'