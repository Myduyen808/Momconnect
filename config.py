import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = 'momconnect_secret_2025'

    # Dùng đường dẫn tuyệt đối để tránh lỗi SQLite không mở được file
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(basedir, 'instance', 'database.db')}"
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(basedir, 'static', 'uploads')
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    
    # Thiết lập múi giờ mặc định cho ứng dụng là Việt Nam (UTC+7)
    TIMEZONE = 'Asia/Ho_Chi_Minh'

    # ===================================================
    # CẤU HÌNH GỬI EMAIL (GMAIL)
    # ===================================================
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False
    
    # ⚠️ THAY ĐỔI EMAIL DƯỚI ĐÂY THÀNH EMAIL GMAIL CỦA BẠN
    MAIL_USERNAME = 'duyenb2203435@student.ctu.edu.vn'      # Ví dụ: minhnguyen123@gmail.com
    
    # DÁN MẬT KHẨU VỪA LẤY VÀO ĐÂY (GIỮ NGUYÊN CÁCH CÁCH NHA)
    MAIL_PASSWORD = 'pvan jwzw ttdc wfjh'               
    
    MAIL_DEFAULT_SENDER = 'MomConnect <duyenb2203435@student.ctu.edu.vn>'