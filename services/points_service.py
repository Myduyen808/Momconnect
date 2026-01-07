# services/points_service.py

from models import db, User, Notification, PointHistory, vietnam_now
from flask_socketio import emit
from flask_login import current_user

# Định nghĩa các mốc điểm
LEVEL_EXPERT_UNLOCK = 2000 

def add_points_for_action(user, action_type, related_id=None, related_user_id=None):
    """
    Thêm điểm cho người dùng và tạo thông báo tương ứng
    
    Args:
        user: Đối tượng User nhận điểm
        action_type: Loại hành động ('post', 'comment', 'receive_like', 'admin_award')
        related_id: ID của đối tượng liên quan (bài viết, bình luận...)
        related_user_id: ID của người dùng liên quan (người like, người bình luận...)
    
    Returns:
        int: Số điểm đã cộng
    """
    points_map = {
        'post': 20,
        'comment': 5,
        'receive_like': 10,
        'admin_award': 50,
        'featured_post': 50
    }
    
    amount = points_map.get(action_type, 0)
    if amount <= 0:
        return 0
    
    # Cập nhật điểm người dùng
    user.points += amount
    
    # Lưu lịch sửữ điểm
    point_history = PointHistory(
        user_id=user.id,
        points_change=amount,
        reason=action_type,
        related_id=related_id
    )
    db.session.add(point_history)
    
    # Tạo thông báo
    messages = {
        'post': f"Bạn đã đăng bài viết mới và nhận được +{amount} điểm",
        'comment': f"Bạn đã bình luận và nhận được +{amount} điểm",
        'receive_like': f"Bài viết của bạn được thích và nhận được +{amount} điểm",
        'admin_award': f"Admin đã thưởng cho bạn +{amount} điểm",
        'featured_post': f"Bài viết của bạn được chọn là hữu ích và nhận được +{amount} điểm"
    }
    
    notification = Notification(
        user_id=user.id,
        title="Thông báo điểm",
        message=messages.get(action_type, f"Bạn nhận được +{amount} điểm"),
        type='point',
        related_id=related_id,
        related_user_id=related_user_id
    )
    db.session.add(notification)
    
    # Kiểm tra xem có đủ điều kiện nộp đơn không
    can_apply, message = user.can_apply_expert()
    if can_apply and not ExpertRequest.query.filter_by(user_id=user.id, status='pending').first():
        # Tạo thông báo đủ điều kiện nộp đơn
        expert_notification = Notification(
            user_id=user.id,
            title="Chúc mừng!",
            message="Bạn đã đủ điều kiện để nộp đơn trở thành chuyên gia. Hãy vào trang cá nhân để đăng ký.",
            type='expert_unlock'
        )
        db.session.add(expert_notification)
    
    db.session.commit()
    
    # Gửi thông báo real-time qua Socket.io
    try:
        emit('new_notification', {
            'message': f"+{amount} điểm: {messages.get(action_type, 'Hành động')}",
            'total_points': user.points,
            'type': 'point'
        }, room=f"user_{user.id}", namespace='/')
    except:
        # Xử lý lỗi nếu không thể gửi thông báo real-time
        pass
    
    return amount

def deduct_points(user, amount, reason, related_id=None):
    """
    Trừ điểm của người dùng
    
    Args:
        user: Đối tượng User bị trừ điểm
        amount: Số điểm bị trừ
        reason: Lý do trừ điểm
        related_id: ID của đối tượng liên quan
    
    Returns:
        int: Số điểm đã trừ
    """
    # Đảm bảo điểm không âm
    amount = min(amount, user.points)
    if amount <= 0:
        return 0
    
    # Cập nhật điểm người dùng
    user.points -= amount
    
    # Lưu lịch sử điểm
    point_history = PointHistory(
        user_id=user.id,
        points_change=-amount,
        reason=reason,
        related_id=related_id
    )
    db.session.add(point_history)
    
    # Tạo thông báo
    notification = Notification(
        user_id=user.id,
        title="Thông báo điểm",
        message=f"Bạn bị trừ {amount} điểm: {reason}",
        type='point',
        related_id=related_id
    )
    db.session.add(notification)
    
    db.session.commit()
    
    # Gửi thông báo real-time qua Socket.io
    try:
        emit('new_notification', {
            'message': f"-{amount} điểm: {reason}",
            'total_points': user.points,
            'type': 'point'
        }, room=f"user_{user.id}", namespace='/')
    except:
        # Xử lý lỗi nếu không thể gửi thông báo real-time
        pass
    
    return amount