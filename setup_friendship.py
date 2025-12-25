# setup_friendship.py - SCRIPT CÀI ĐẶT HỆ THỐNG KẾT BẠN

import os

def setup_friendship_system():
    """Copy tất cả các file cần thiết vào project hiện tại"""
    
    print("🚀 Bắt đầu cài đặt hệ thống kết bạn...")
    
    # Nội dung file friendship_routes.py
    friendship_routes_content = '''# friendship_routes.py - ROUTES CHO HỆ THỐNG KẾT BẠN
from flask import jsonify, request, render_template
from flask_login import login_required, current_user
from models import User, Friendship, FriendRequest, Notification
from database import db
from datetime import datetime
from sqlalchemy import func

# === GỬI LỜI MỜI KẾT BẠN ===
def send_friend_request(user_id):
    recipient = User.query.get_or_404(user_id)
    
    if recipient.id == current_user.id:
        return jsonify({'error': 'Không thể gửi lời mời cho chính mình!'}), 400
    
    # Kiểm tra đã là bạn bè chưa
    if current_user.is_friends_with(user_id):
        return jsonify({'error': 'Đã là bạn bè rồi!'}), 400
    
    # Kiểm tra đã có lời mời nào chưa
    if current_user.has_pending_friend_request_to(user_id):
        return jsonify({'error': 'Đã gửi lời mời trước đó!'}), 400
    
    if current_user.has_pending_friend_request_from(user_id):
        return jsonify({'error': 'Người này đã gửi lời mời cho bạn!'}), 400
    
    # Tạo lời mời kết bạn mới
    friend_request = FriendRequest(
        sender_id=current_user.id,
        receiver_id=user_id,
        status='pending'
    )
    db.session.add(friend_request)
    
    # Tạo thông báo cho người nhận
    notification = Notification(
        user_id=user_id,
        title="Lời mời kết bạn mới!",
        message=f"{current_user.name} đã gửi lời mời kết bạn cho bạn.",
        type='friend_request',
        related_user_id=current_user.id
    )
    db.session.add(notification)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Đã gửi lời mời kết bạn tới {recipient.name}!',
        'status': 'outgoing_request'
    })

# === CHẤP NHẬN LỜI MỜI KẾT BẠN ===
def accept_friend_request(request_id):
    friend_request = FriendRequest.query.get_or_404(request_id)
    
    # Kiểm tra xem lời mời có dành cho current_user không
    if friend_request.receiver_id != current_user.id:
        return jsonify({'error': 'Không có quyền xử lý lời mời này!'}), 403
    
    if friend_request.status != 'pending':
        return jsonify({'error': 'Lời mời đã được xử lý!'}), 400
    
    # Cập nhật trạng thái lời mời
    friend_request.status = 'accepted'
    friend_request.updated_at = vietnam_now()
    
    # Tạo quan hệ bạn bè
    friendship = Friendship(
        user1_id=friend_request.sender_id,
        user2_id=current_user.id
    )
    db.session.add(friendship)
    
    # Tạo thông báo cho người gửi
    notification = Notification(
        user_id=friend_request.sender_id,
        title="Lời mời được chấp nhận!",
        message=f"{current_user.name} đã chấp nhận lời mời kết bạn của bạn.",
        type='friend_accepted',
        related_user_id=current_user.id
    )
    db.session.add(notification)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Đã kết bạn với {friend_request.sender.name}!',
        'status': 'friends'
    })

# === TỪ CHỐI LỜI MỜI KẾT BẠN ===
def reject_friend_request(request_id):
    friend_request = FriendRequest.query.get_or_404(request_id)
    
    # Kiểm tra xem lời mời có dành cho current_user không
    if friend_request.receiver_id != current_user.id:
        return jsonify({'error': 'Không có quyền xử lý lời mời này!'}), 403
    
    if friend_request.status != 'pending':
        return jsonify({'error': 'Lời mời đã được xử lý!'}), 400
    
    # Cập nhật trạng thái lời mời
    friend_request.status = 'rejected'
    friend_request.updated_at = vietnam_now()
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Đã từ chối lời mời kết bạn!',
        'status': 'not_friends'
    })

# === HỦY LỜI MỜI KẾT BẠN ===
def cancel_friend_request(user_id):
    # Tìm lời mời đã gửi
    friend_request = FriendRequest.query.filter_by(
        sender_id=current_user.id,
        receiver_id=user_id,
        status='pending'
    ).first()
    
    if not friend_request:
        return jsonify({'error': 'Không tìm thấy lời mời!'}), 404
    
    db.session.delete(friend_request)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Đã hủy lời mời kết bạn!',
        'status': 'not_friends'
    })

# === HỦY KẾT BẠN ===
def unfriend(user_id):
    # Tìm quan hệ bạn bè
    friendship = Friendship.query.filter(
        ((Friendship.user1_id == current_user.id) & (Friendship.user2_id == user_id)) |
        ((Friendship.user1_id == user_id) & (Friendship.user2_id == current_user.id))
    ).first()
    
    if not friendship:
        return jsonify({'error': 'Không phải là bạn bè!'}), 404
    
    db.session.delete(friendship)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Đã hủy kết bạn!',
        'status': 'not_friends'
    })

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

# === CẬP NHẬT TRANG FRIENDS ===
def friends():
    # Lấy danh sách bạn bè
    friends_list = current_user.friends
    
    # Lấy danh sách lời mời đang chờ
    pending_requests = current_user.get_pending_friend_requests()
    
    # Lấy danh sách lời mời đã gửi
    sent_requests = current_user.get_sent_friend_requests()
    
    # Gợi ý kết bạn - những người không phải bạn bè và chưa có lời mời
    friend_ids = [f.id for f in friends_list] + [current_user.id]
    
    # Lấy ID của những người đã có lời mời
    pending_sender_ids = [req.sender_id for req in pending_requests]
    pending_receiver_ids = [req.receiver_id for req in sent_requests]
    excluded_ids = friend_ids + pending_sender_ids + pending_receiver_ids
    
    suggested_users = User.query.filter(
        ~User.id.in_(excluded_ids)
    ).order_by(func.random()).limit(10).all()

    return render_template(
        'friends.html',
        friends=friends_list,
        pending_requests=pending_requests,
        sent_requests=sent_requests,
        suggested_users=suggested_users
    )
'''

    # Nội dung file friendship_status_route.py
    friendship_status_content = '''# friendship_status_route.py - ROUTE KIỂM TRA TRẠNG THÁI KẾT BẠN
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
'''

    # Tạo các file
    files_to_create = {
        'friendship_routes.py': friendship_routes_content,
        'friendship_status_route.py': friendship_status_content,
    }
    
    for filename, content in files_to_create.items():
        if not os.path.exists(filename):
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Đã tạo file: {filename}")
        else:
            print(f"⚠️ File {filename} đã tồn tại, bỏ qua")
    
    print("\n🎉 Hoàn tất cài đặt!")
    print("\n📝 Các bước tiếp theo:")
    print("1. Xóa dòng import lỗi trong app.py")
    print("2. Thêm các route vào app.py")
    print("3. Khởi động lại ứng dụng")
    print("\n📋 Cần thêm vào app.py:")
    print("from friendship_routes import *")
    print("from friendship_status_route import *")

if __name__ == '__main__':
    setup_friendship_system()