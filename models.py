# models.py - SỬA HOÀN CHỈNH
from database import db
from flask_login import UserMixin
from datetime import datetime, timedelta
from flask import url_for
import pytz  # Import thư viện pyt
from sqlalchemy import event

# THAY VÀO ĐÓ, TẠO MỘT HÀM MỚI


def vietnam_now():
    return datetime.utcnow() + timedelta(hours=7)

# ĐỊNH NGHĨA FOLLOW TRƯỚC USER
class Follow(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    follower_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    followed_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=vietnam_now)
    
    # STRING REFERENCE - tránh circular import
    follower = db.relationship('User', foreign_keys=[follower_id], 
                              backref=db.backref('following', lazy='dynamic'))
    followed = db.relationship('User', foreign_keys=[followed_id], 
                              backref=db.backref('followers', lazy='dynamic'))
    
# MODEL FRIENDSHIP - BẠN BÈ THẬT SỰ (ĐÃ CHẤP NHẬN LỜI MỜI)
class Friendship(db.Model):
    __tablename__ = 'friendship'
    id = db.Column(db.Integer, primary_key=True)
    user1_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user2_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=vietnam_now)
    
    # Relationships
    user1 = db.relationship('User', foreign_keys=[user1_id], 
                           backref=db.backref('friendships_initiated', lazy='dynamic'))
    user2 = db.relationship('User', foreign_keys=[user2_id], 
                           backref=db.backref('friendships_received', lazy='dynamic'))
    
    # Đảm bảo mỗi cặp bạn bè chỉ tồn tại 1 lần
    __table_args__ = (db.UniqueConstraint('user1_id', 'user2_id', name='unique_friendship'),)

# MODEL FRIEND REQUEST - LỜI MỜI KẾT BẠN
class FriendRequest(db.Model):
    __tablename__ = 'friend_request'
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, accepted, rejected
    created_at = db.Column(db.DateTime, default=vietnam_now)
    updated_at = db.Column(db.DateTime, default=vietnam_now, onupdate=vietnam_now)
    
    # Relationships
    sender = db.relationship('User', foreign_keys=[sender_id], 
                            backref=db.backref('friend_requests_sent', lazy='dynamic'))
    receiver = db.relationship('User', foreign_keys=[receiver_id], 
                               backref=db.backref('friend_requests_received', lazy='dynamic'))
    
    # Đảm bảo mỗi cặp người dùng chỉ có 1 lời mời đang chờ
    __table_args__ = (db.UniqueConstraint('sender_id', 'receiver_id', name='unique_friend_request'),)

# SAU ĐÓ MỚI USER
class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    avatar = db.Column(db.String(200), default='default.jpg')
    bio = db.Column(db.Text)
    children_count = db.Column(db.Integer, default=0)
    children_ages = db.Column(db.String(100))
    points = db.Column(db.Integer, default=0)
    role = db.Column(db.String(20), default='user')
    is_active = db.Column(db.Boolean, default=True)
    is_verified_expert = db.Column(db.Boolean, default=False)
    expert_category = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=vietnam_now)

    # Relationships
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    # comments = db.relationship('Comment', backref='author', lazy='dynamic')


    @property
    def avatar_url(self):
        if self.avatar and self.avatar != 'default.jpg':
            return url_for('static', filename=f'uploads/{self.avatar}')
        return url_for('static', filename='images/default-avatar.png')
    
    @property
    def friends(self):
        """Lấy danh sách bạn bè thực sự (đã chấp nhận lời mời)"""
        friendships = Friendship.query.filter(
            (Friendship.user1_id == self.id) | (Friendship.user2_id == self.id)
        ).all()
        
        friend_ids = []
        for friendship in friendships:
            if friendship.user1_id == self.id:
                friend_ids.append(friendship.user2_id)
            else:
                friend_ids.append(friendship.user1_id)
        
        return User.query.filter(User.id.in_(friend_ids)).all()
    
    def is_friends_with(self, user_id):
        """Kiểm tra có phải là bạn bè không"""
        return Friendship.query.filter(
            ((Friendship.user1_id == self.id) & (Friendship.user2_id == user_id)) |
            ((Friendship.user1_id == user_id) & (Friendship.user2_id == self.id))
        ).first() is not None
    
    def has_pending_friend_request_from(self, user_id):
        """Kiểm tra có lời mời kết bạn từ user_id không"""
        return FriendRequest.query.filter_by(
            sender_id=user_id, 
            receiver_id=self.id, 
            status='pending'
        ).first() is not None
    
    def has_pending_friend_request_to(self, user_id):
        """Kiểm tra đã gửi lời mời kết bạn đến user_id chưa"""
        return FriendRequest.query.filter_by(
            sender_id=self.id, 
            receiver_id=user_id, 
            status='pending'
        ).first() is not None
    
    def get_friendship_status(self, user_id):
        """Lấy trạng thái kết bạn với user_id"""
        if self.id == user_id:
            return 'self'
        
        if self.is_friends_with(user_id):
            return 'friends'
        
        if self.has_pending_friend_request_from(user_id):
            return 'incoming_request'
        
        if self.has_pending_friend_request_to(user_id):
            return 'outgoing_request'
        
        return 'not_friends'
    
    def get_pending_friend_requests(self):
        """Lấy danh sách lời mời kết bạn đang chờ xử lý"""
        return FriendRequest.query.filter_by(
            receiver_id=self.id, 
            status='pending'
        ).order_by(FriendRequest.created_at.desc()).all()
    
    def get_sent_friend_requests(self):
        """Lấy danh sách lời mời đã gửi"""
        return FriendRequest.query.filter_by(
            sender_id=self.id, 
            status='pending'
        ).order_by(FriendRequest.created_at.desc()).all()

    # Thêm vào class User
    @property
    def can_request_expert(self):
        """ ĐIỂM CHỈ LÀ HOẠT ĐỘNG - AI CŨNG CÓ THỂ NỘP ĐƠN"""
        # Chỉ kiểm tra: chưa phải chuyên gia + chưa có yêu cầu pending
        if self.is_verified_expert:
            return False
        
        pending = ExpertRequest.query.filter_by(
            user_id=self.id,
            status='pending'
        ).first()
        
        return pending is None  # ← CHỈ CẦN CHƯA CÓ YÊU CẦU PENDING

    def get_expert_progress(self):
        """✅ BỎ HẲN PHẦN TÍNH PHẦN TRĂM - CHỈ TRẢ VỀ ĐIỂM HOẠT ĐỘNG"""
        total_posts = self.posts.count()
        total_comments = Comment.query.filter_by(user_id=self.id).count()
        
        return {
            'points': self.points,
            'total_posts': total_posts,
            'total_comments': total_comments,
            'activity_level': (
                'Rất tích cực' if self.points > 2000 else
                'Tích cực' if self.points > 1000 else
                'Hoạt động' if self.points > 200 else
                'Mới tham gia'
            )
        }
    
class Post(db.Model):
    __tablename__ = 'posts' 
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    images = db.Column(db.Text)  # "img1.jpg,img2.jpg"
    video = db.Column(db.String(200))
    category = db.Column(db.String(50), default='other')
    post_type = db.Column(db.String(20), default='question')  # 'question' hoặc 'sharing'
    is_expert_post = db.Column(db.Boolean, default=False)
    likes = db.Column(db.Integer, default=0)
    comments_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=vietnam_now)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_helpful = db.Column(db.Boolean, default=False)  # THÊM DÒNG NÀY
    views = db.Column(db.Integer, default=0)

    # THÊM 2 DÒNG NÀY
    rating = db.Column(db.Float, default=0.0)  # Điểm trung bình
    rating_count = db.Column(db.Integer, default=0) # Số lượt đánh giá

    def get_images_list(self):
        if not self.images:
            return []
        all_files = self.images.split(',')
        return [f for f in all_files if not f.lower().endswith(('.mp4', '.mov', '.avi', '.webm'))]

    def get_media_files(self):
        files = []
        if self.images:
            files.extend(self.images.split(','))
        if self.video:
            files.append(self.video)
        return files
    
# MODEL POST LIKE
class PostLike(db.Model):
    __tablename__ = 'post_like'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=vietnam_now)
    
    user = db.relationship('User', backref='post_likes')
    post = db.relationship('Post', backref='post_likes')
    
    __table_args__ = (db.UniqueConstraint('user_id', 'post_id', name='unique_post_like'),)

# MODEL HIDDEN POST
class HiddenPost(db.Model):
    __tablename__ = 'hidden_post'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=vietnam_now)
    
    __table_args__ = (db.UniqueConstraint('user_id', 'post_id', name='unique_hidden_post'),)

# MODEL POST RATING
class PostRating(db.Model):
    __tablename__ = 'post_rating'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    stars = db.Column(db.Integer, nullable=False)  # 1-5
    created_at = db.Column(db.DateTime, default=vietnam_now)
    
    user = db.relationship('User', backref='post_ratings')
    post = db.relationship('Post', backref='post_ratings')
    
    __table_args__ = (db.UniqueConstraint('user_id', 'post_id', name='unique_post_rating'),)

    

# Thêm vào models.py

class ExpertRequest(db.Model):
    __tablename__ = 'expert_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    certificate = db.Column(db.String(200))  # Đường dẫn đến ảnh bằng cấp
    reason = db.Column(db.Text, nullable=False)  # Lý do muốn trở thành chuyên gia
    category = db.Column(db.String(50))  # Lĩnh vực chuyên môn
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    admin_note = db.Column(db.Text)  # Ghi chú của admin
    created_at = db.Column(db.DateTime, default=vietnam_now)
    updated_at = db.Column(db.DateTime, default=vietnam_now, onupdate=vietnam_now)
    
    # Relationships
    user = db.relationship('User', backref='expert_requests')


# Thêm vào models.py

class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('comments.id'), nullable=True)
    
    # Media
    image = db.Column(db.String(500), nullable=True)
    video = db.Column(db.String(500), nullable=True)
    sticker = db.Column(db.String(200), nullable=True)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=vietnam_now)
    updated_at = db.Column(db.DateTime, default=vietnam_now, onupdate=vietnam_now)
    is_edited = db.Column(db.Boolean, default=False)
    is_spam = db.Column(db.Boolean, default=False)
    
    # Relationships
    author = db.relationship('User', backref='comments')
    post = db.relationship('Post', backref='all_comments')
    replies = db.relationship('Comment', 
                             backref=db.backref('parent', remote_side=[id]),
                             lazy='dynamic',
                             cascade='all, delete-orphan')
    likes = db.relationship('CommentLike', backref='comment', lazy='dynamic', cascade='all, delete-orphan')
    reports = db.relationship('CommentReport', backref='comment', lazy='dynamic', cascade='all, delete-orphan')
    
    @property
    def likes_count(self):
        return self.likes.count()
    
    @property
    def replies_count(self):
        return self.replies.filter_by(is_spam=False).count()
    
    def is_liked_by(self, user_id):
        return self.likes.filter_by(user_id=user_id).first() is not None
    
    def can_edit(self, user):
        return self.user_id == user.id
    
    def can_delete(self, user):
        return self.user_id == user.id or user.role == 'admin' or self.post.user_id == user.id

# ✅ MODEL COMMENT LIKE (THÊM MỚI)
class CommentLike(db.Model):
    __tablename__ = 'comment_likes'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    comment_id = db.Column(db.Integer, db.ForeignKey('comments.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=vietnam_now)
    
    __table_args__ = (db.UniqueConstraint('user_id', 'comment_id', name='unique_comment_like'),)


# ✅ MODEL COMMENT REPORT (THÊM MỚI)
class CommentReport(db.Model):
    __tablename__ = 'comment_reports'
    id = db.Column(db.Integer, primary_key=True)
    comment_id = db.Column(db.Integer, db.ForeignKey('comments.id'), nullable=False)
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reason = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=vietnam_now)
    
    reporter = db.relationship('User', backref='comment_reports')

# Thêm vào models.py

class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(20))  # point, expert_request, system, like, comment
    related_id = db.Column(db.Integer)  # ID của đối tượng liên quan (bài viết, bình luận...)
    related_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))  # ID của người dùng liên quan
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=vietnam_now)
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='notifications')
    related_user = db.relationship('User', foreign_keys=[related_user_id])


class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reason = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=vietnam_now)

    post = db.relationship('Post', backref='reports')
    user = db.relationship('User', backref='reports')

# THÊM VÀO FILE models.py

# Cập nhật class Message
class Message(db.Model):
    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(20), default='text')
    timestamp = db.Column(db.DateTime, default=vietnam_now)
    is_read = db.Column(db.Boolean, default=False)

    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='received_messages')

# models.py - DÁN ĐOẠN NÀY VÀO CUỐI FILE

# Thêm model PointHistory để theo dõi thay đổi điểm

class PointHistory(db.Model):
    __tablename__ = 'point_history'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    points_change = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(255), nullable=False)
    related_id = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=vietnam_now)
    
    # Relationships
    user = db.relationship('User', backref='point_history')

@event.listens_for(db.session, 'before_flush')
def set_timestamps_before_flush(session, context, instances):
    """
    Tự động đặt created_at và updated_at cho các model trước khi lưu vào DB.
    Đây là cách đáng tin cậy nhất để đảm bảo timezone đúng.
    """
    for instance in session.new:
        # Đối với các đối tượng MỚI
        if hasattr(instance, 'created_at') and instance.created_at is None:
            instance.created_at = vietnam_now()
        if hasattr(instance, 'updated_at'):
            instance.updated_at = vietnam_now()

    for instance in session.dirty:
        # Đối với các đối tượng ĐÃ CÓ NHƯNG BỊ SỬA
        if hasattr(instance, 'updated_at'):
            instance.updated_at = vietnam_now()

