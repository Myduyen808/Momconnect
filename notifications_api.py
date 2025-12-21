from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from models import Notification, db
from datetime import datetime

notifications_api = Blueprint('notifications_api', __name__)

@notifications_api.route('/api/notifications', methods=['GET'])
@login_required
def get_notifications():
    """Lấy danh sách thông báo của user hiện tại"""
    try:
        notifications = Notification.query.filter_by(
            user_id=current_user.id
        ).order_by(Notification.created_at.desc()).limit(20).all()
        
        notif_list = []
        for notif in notifications:
            # Xác định avatar người liên quan
            avatar_url = '/static/uploads/default.jpg'
            if notif.related_user and notif.related_user.avatar:
                avatar_url = f"/static/{notif.related_user.avatar}"
            
            # Format thời gian
            time_str = notif.created_at.strftime('%H:%M %d/%m/%Y')
            
            notif_data = {
                'id': notif.id,
                'title': notif.title,
                'message': notif.message,
                'type': notif.type,
                'is_read': notif.is_read,
                'created_at': time_str,
                'related_user_avatar': avatar_url,
                'related_user_id': notif.related_user_id,
                'post_id': notif.post_id,
                'comment_id': notif.comment_id
            }
            notif_list.append(notif_data)
        
        return jsonify(notif_list)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@notifications_api.route('/api/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    """Đánh dấu thông báo đã đọc"""
    try:
        notification = Notification.query.filter_by(
            id=notification_id,
            user_id=current_user.id
        ).first()
        
        if not notification:
            return jsonify({'error': 'Notification not found'}), 404
        
        notification.is_read = True
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@notifications_api.route('/api/notifications/read-all', methods=['POST'])
@login_required
def mark_all_notifications_read():
    """Đánh dấu tất cả thông báo đã đọc"""
    try:
        Notification.query.filter_by(
            user_id=current_user.id,
            is_read=False
        ).update({'is_read': True})
        
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@notifications_api.route('/notifications/count', methods=['GET'])
@login_required
def get_notification_count():
    """Lấy số lượng thông báo chưa đọc"""
    try:
        count = Notification.query.filter_by(
            user_id=current_user.id,
            is_read=False
        ).count()
        
        return jsonify({'count': count})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500