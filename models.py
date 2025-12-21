# models.py - SỬA HOÀN CHỈNH
from database import db
from flask_login import UserMixin
from datetime import datetime
from flask import url_for

# ĐỊNH NGHĨA FOLLOW TRƯỚC USER
class Follow(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    follower_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    followed_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # STRING REFERENCE - tránh circular import
    follower = db.relationship('User', foreign_keys=[follower_id], 
                              backref=db.backref('following', lazy='dynamic'))
    followed = db.relationship('User', foreign_keys=[followed_id], 
                              backref=db.backref('followers', lazy='dynamic'))
    
# MODEL FRIENDSHIP - BẠN BÈ THẬT SỰ (ĐÃ CHẤP NHẬN LỜI MỜI)
class Friendship(db.Model):
    __tablename__ = 'friendship'
    id = db.Column(db.Integer, primary_key=True)
    user1_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user2_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
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
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, accepted, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    sender = db.relationship('User', foreign_keys=[sender_id], 
                            backref=db.backref('friend_requests_sent', lazy='dynamic'))
    receiver = db.relationship('User', foreign_keys=[receiver_id], 
                               backref=db.backref('friend_requests_received', lazy='dynamic'))
    
    # Đảm bảo mỗi cặp người dùng chỉ có 1 lời mời đang chờ
    __table_args__ = (db.UniqueConstraint('sender_id', 'receiver_id', name='unique_friend_request'),)

# SAU ĐÓ MỚI USER
class User(UserMixin, db.Model):
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
    expert_request = db.Column(db.Text)
    expert_category = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    posts = db.relationship('Post', foreign_keys='Post.user_id', backref='author', lazy='dynamic')
    comments = db.relationship('Comment', backref='author', lazy='dynamic')
    expert_requests = db.relationship('ExpertRequest', backref='user', lazy='dynamic')

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


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    images = db.Column(db.Text)  # "img1.jpg,img2.jpg"
    video = db.Column(db.String(200))
    category = db.Column(db.String(50), default='other')
    is_expert_post = db.Column(db.Boolean, default=False)
    likes = db.Column(db.Integer, default=0)
    comments_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

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

class ExpertRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    certificate = db.Column(db.String(200))
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    admin_note = db.Column(db.Text)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Notification(db.Model):
    __tablename__ = 'notification'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(20))
    related_id = db.Column(db.Integer)
    related_user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    related_user = db.relationship('User', foreign_keys=[related_user_id])

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reason = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    post = db.relationship('Post', backref='reports')
    user = db.relationship('User', backref='reports')

# THÊM VÀO FILE models.py

# Cập nhật class Message
class Message(db.Model):
    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(20), default='text')
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)

    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='received_messages')

