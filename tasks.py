from apscheduler.schedulers.background import BackgroundScheduler
from flask_mail import Mail, Message
from datetime import datetime, timedelta
from database import db
import pytz

mail = Mail()

def check_and_send_consultation_reminders(app):
    """Chạy mỗi phút: Kiểm tra lịch tư vấn -> Gửi Email (30p) và Popup (15p)"""
    with app.app_context():
        from app import socketio
        from models import Notification
        
        # Dùng DATETIME NAIVE để so sánh an toàn với SQLite
        now = datetime.now(pytz.timezone('Asia/Ho_Chi_Minh')).replace(tzinfo=None)
        
        # Tìm lịch sắp diễn ra trong 30 phút tới
        soon_30m = now + timedelta(minutes=30)
        upcoming = Booking.query.filter_by(status='scheduled')\
                               .join(TimeSlot)\
                               .filter(TimeSlot.start_time.between(now, soon_30m))\
                               .all()
        
        for booking in upcoming:
            time_diff = (booking.time_slot.start_time - now).total_seconds() / 60
            expert = booking.time_slot.expert
            user = booking.user
            start_time_str = booking.time_slot.start_time.strftime('%H:%M %d/%m/%Y')

            # ==========================================
            # 1. GỬI EMAIL KHI CÒN 28 - 31 PHÚT
            # ==========================================
            if 28 <= time_diff <= 31:
                # Kiểm tra đã gửi email chưa (tránh spam)
                existing_email = Notification.query.filter_by(
                    type='email_reminder_30m',
                    related_id=booking.id
                ).first()
                
                if not existing_email:
                    # Đánh dấu đã gửi email vào DB
                    notif_flag = Notification(
                        user_id=user.id, 
                        type='email_reminder_30m', 
                        related_id=booking.id, 
                        title="Đã gửi email nhắc 30p", 
                        message=""
                    )
                    db.session.add(notif_flag)
                    db.session.commit()
                    
                    # Gửi Email cho User
                    try:
                        msg = Message(
                            subject=f'⏰ Nhắc nhở: Buổi tư vấn lúc {start_time_str}',
                            recipients=[user.email],
                            body=f"""Chào {user.name},

Buổi tư vấn của bạn với chuyên gia {expert.name} sẽ bắt đầu vào lúc {start_time_str} (còn 30 phút nữa).

Vui lòng truy cập MomConnect, vào mục "Lịch hẹn của tôi" để chuẩn bị nhé!

Trân trọng,
MomConnect Team
"""
                        )
                        mail.send(msg)
                        print(f"✅ Đã gửi email cho User: {user.email}")
                    except Exception as e:
                        print(f"❌ Lỗi gửi email User: {e}")
                    
                    # Gửi Email cho Expert
                    try:
                        msg_exp = Message(
                            subject=f'⏰ Nhắc nhở: Lịch tư vấn lúc {start_time_str}',
                            recipients=[expert.email],
                            body=f"""Chào {expert.name},

Bạn có lịch tư vấn với khách hàng {user.name} vào lúc {start_time_str}.

Vui lòng đăng nhập MomConnect và chuẩn bị trước.

Trân trọng,
MomConnect Team
"""
                        )
                        mail.send(msg_exp)
                        print(f"✅ Đã gửi email cho Expert: {expert.email}")
                    except Exception as e:
                        print(f"❌ Lỗi gửi email Expert: {e}")

            # ==========================================
            # 2. POPUP NHẮC NHỞ KHI CÒN 13 - 16 PHÚT
            # ==========================================
            elif 13 <= time_diff <= 16:
                existing_reminder = Notification.query.filter_by(
                    type='booking_reminder',
                    related_id=booking.id
                ).first()
                
                if not existing_reminder:
                    notif_user = Notification(
                        user_id=user.id, title="⏰ Lịch tư vấn sắp bắt đầu!",
                        message=f"Buổi tư vấn với {expert.name} sẽ bắt đầu vào lúc {start_time_str}.",
                        type='booking_reminder', related_id=booking.id, related_user_id=expert.id
                    )
                    db.session.add(notif_user)
                    
                    notif_expert = Notification(
                        user_id=expert.id, title="⏰ Khách hàng sắp đến giờ!",
                        message=f"{user.name} có lịch vào lúc {start_time_str}.",
                        type='booking_reminder', related_id=booking.id, related_user_id=user.id
                    )
                    db.session.add(notif_expert)
                    db.session.commit()
                    
                    # Gửi realtime Socket
                    try:
                        socketio.emit('consultation_reminder', {
                            'title': '⏰ Lịch tư vấn sắp bắt đầu!', 'message': f"Buổi tư vấn với {expert.name} sẽ bắt đầu vào lúc {start_time_str}",
                            'booking_id': booking.id, 'expert_id': expert.id, 'expert_name': expert.name,
                            'avatar': expert.avatar or 'images/default-avatar.png'
                        }, room=f"user_{user.id}")
                        
                        socketio.emit('consultation_reminder', {
                            'title': '⏰ Khách hàng sắp đến giờ!', 'message': f"{user.name} có lịch vào lúc {start_time_str}",
                            'booking_id': booking.id, 'user_id': user.id, 'user_name': user.name,
                            'avatar': user.avatar or 'images/default-avatar.png'
                        }, room=f"user_{expert.id}")
                    except Exception as e:
                        print(f"Lỗi socket: {e}")

# Khởi tạo scheduler
scheduler = BackgroundScheduler()