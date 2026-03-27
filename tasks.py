# Tạo file tasks.py
from apscheduler.schedulers.background import BackgroundScheduler
from flask_mail import Mail, Message
from datetime import datetime, timedelta

mail = Mail()

def send_reminder_emails():
    """Chạy mỗi giờ để gửi email nhắc nhở"""
    now = vietnam_now()
    
    # Lấy booking sắp diễn ra trong 1-2h
    upcoming = Booking.query.filter_by(status='scheduled')\
                           .join(TimeSlot)\
                           .filter(
                               TimeSlot.start_time >= now,
                               TimeSlot.start_time <= now + timedelta(hours=2)
                           ).all()
    
    for booking in upcoming:
        time_diff = (booking.time_slot.start_time - now).total_seconds() / 60
        
        # Gửi email 1h trước
        if 55 <= time_diff <= 65:
            send_email(
                to=booking.user.email,
                subject='Nhắc nhở: Buổi tư vấn sắp bắt đầu',
                body=f'Buổi tư vấn của bạn với {booking.time_slot.expert.name} sẽ bắt đầu lúc {booking.time_slot.start_time.strftime("%H:%M")}.'
            )

def send_email(to, subject, body):
    msg = Message(subject, recipients=[to], body=body)
    mail.send(msg)

# Khởi tạo scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(send_reminder_emails, 'interval', hours=1)
scheduler.start()