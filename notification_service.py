from models import Notification
from models import Notification, db

class NotificationService:
    """Service để xử lý logic liên quan đến thông báo"""
    
    @staticmethod
    def create_notification(user_id, title, message, notif_type, 
                          related_user_id=None, post_id=None, comment_id=None):
        """Tạo thông báo mới với redirect URL tự động"""
        try:
            notif = Notification(
                user_id=user_id,
                title=title,
                message=message,
                type=notif_type,
                related_user_id=related_user_id,
                post_id=post_id,
                comment_id=comment_id,
                is_read=False
            )
            
            db.session.add(notif)
            db.session.commit()
            return notif
            
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def get_redirect_url(notification):
        """Xác định URL redirect dựa trên loại thông báo"""
        if notification.type == 'comment' and notification.post_id:
            # Nếu là comment, chuyển đến bài viết và scroll đến comment
            comment_hash = f"#comment-{notification.comment_id}" if notification.comment_id else ""
            return f"/post/{notification.post_id}{comment_hash}"
        elif notification.type == 'like' and notification.post_id:
            # Nếu là like, chuyển đến bài viết
            return f"/post/{notification.post_id}"
        elif notification.type == 'follow' and notification.related_user_id:
            # Nếu là follow, chuyển đến profile người theo dõi
            return f"/profile/{notification.related_user_id}"
        else:
            return "#"
    
    @staticmethod
    def create_like_notification(post_owner_id, liker_user_id, post_id):
        """Tạo thông báo khi có người like bài viết"""
        from models import User
        
        liker = User.query.get(liker_user_id)
        if not liker:
            return None
            
        title = f"{liker.username} đã thích bài đăng của bạn"
        message = "Nhấn để xem bài viết"
        
        return NotificationService.create_notification(
            user_id=post_owner_id,
            title=title,
            message=message,
            notif_type='like',
            related_user_id=liker_user_id,
            post_id=post_id
        )
    
    @staticmethod
    def create_comment_notification(post_owner_id, commenter_user_id, post_id, comment_id=None):
        """Tạo thông báo khi có người bình luận bài viết"""
        from models import User
        
        commenter = User.query.get(commenter_user_id)
        if not commenter:
            return None
            
        title = f"{commenter.username} đã bình luận bài đăng của bạn"
        message = "Nhấn để xem bình luận"
        
        return NotificationService.create_notification(
            user_id=post_owner_id,
            title=title,
            message=message,
            notif_type='comment',
            related_user_id=commenter_user_id,
            post_id=post_id,
            comment_id=comment_id
        )
    
    @staticmethod
    def create_follow_notification(followed_user_id, follower_user_id):
        """Tạo thông báo khi có người theo dõi"""
        from models import User
        
        follower = User.query.get(follower_user_id)
        if not follower:
            return None
            
        title = f"{follower.username} đã bắt đầu theo dõi bạn"
        message = "Nhấn để xem hồ sơ của họ"
        
        return NotificationService.create_notification(
            user_id=followed_user_id,
            title=title,
            message=message,
            notif_type='follow',
            related_user_id=follower_user_id
        )