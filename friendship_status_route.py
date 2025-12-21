# friendship_status_route.py - ROUTE KIỂM TRA TRẠNG THÁI KẾT BẠN
from flask import jsonify
from flask_login import login_required, current_user
from models import User, FriendRequest

# === LẤY TRẠNG THÁI KẾT BẠN ===
def friendship_status(user_id):
    status = current_user.get_friendship_status(user_id)
    
    # Nếu có lời mời đến, trả về ID của nó
    pending_request_id = None
    if status == 'incoming_request':
        request = FriendRequest.query.filter_by(
            sender_id=user_id, 
            receiver_id=current_user.id, 
            status='pending'
        ).first()
        if request:
            pending_request_id = request.id
    
    return jsonify({
        'status': status,
        'user_id': user_id,
        'pending_request_id': pending_request_id
    })
