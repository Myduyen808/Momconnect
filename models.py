# models.py - CẬP NHẬT HOÀN CHỈNH CHO CHUYÊN GIA
from database import db
from flask_login import UserMixin
from datetime import datetime, timedelta
from flask import url_for
import pytz
from sqlalchemy import event

def vietnam_now():
    return datetime.utcnow() + timedelta(hours=7)

# =====================================================
# FOLLOW MODEL
# =====================================================
class Follow(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    follower_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    followed_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=vietnam_now)
    
    follower = db.relationship('User', foreign_keys=[follower_id], 
                              backref=db.backref('following', lazy='dynamic'))
    followed = db.relationship('User', foreign_keys=[followed_id], 
                              backref=db.backref('followers', lazy='dynamic'))

# =====================================================
# FRIENDSHIP MODEL
# =====================================================
class Friendship(db.Model):
    __tablename__ = 'friendship'
    id = db.Column(db.Integer, primary_key=True)
    user1_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user2_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=vietnam_now)
    
    user1 = db.relationship('User', foreign_keys=[user1_id], 
                           backref=db.backref('friendships_initiated', lazy='dynamic'))
    user2 = db.relationship('User', foreign_keys=[user2_id], 
                           backref=db.backref('friendships_received', lazy='dynamic'))
    
    __table_args__ = (db.UniqueConstraint('user1_id', 'user2_id', name='unique_friendship'),)

# =====================================================
# FRIEND REQUEST MODEL
# =====================================================
class FriendRequest(db.Model):
    __tablename__ = 'friend_request'
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=vietnam_now)
    updated_at = db.Column(db.DateTime, default=vietnam_now, onupdate=vietnam_now)
    
    sender = db.relationship('User', foreign_keys=[sender_id], 
                            backref=db.backref('friend_requests_sent', lazy='dynamic'))
    receiver = db.relationship('User', foreign_keys=[receiver_id], 
                               backref=db.backref('friend_requests_received', lazy='dynamic'))
    
    __table_args__ = (db.UniqueConstraint('sender_id', 'receiver_id', name='unique_friend_request'),)

# =====================================================
# USER MODEL - ĐÃ CẬP NHẬT ĐẦY ĐỦ
# =====================================================
class User(UserMixin, db.Model):
    __tablename__ = 'users'

    # ===== THÔNG TIN CƠ BẢN =====
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    avatar = db.Column(db.String(200), default='default.jpg')
    bio = db.Column(db.Text)
    phone = db.Column(db.String(15), unique=True)  # Số điện thoại
    
    # ===== THÔNG TIN GIA ĐÌNH =====
    children_count = db.Column(db.Integer, default=0)
    children_ages = db.Column(db.String(100))
    
    # ===== HỆ THỐNG =====
    points = db.Column(db.Integer, default=0)
    role = db.Column(db.String(20), default='user')  # user, admin, expert
    is_active = db.Column(db.Boolean, default=True)
    badge = db.Column(db.String(50))  # ← THÊM TRƯỜNG CẤP BẬC
    created_at = db.Column(db.DateTime, default=vietnam_now)
    
    # ===== CHUYÊN GIA - TRẠNG THÁI =====
    is_verified_expert = db.Column(db.Boolean, default=False)
    expert_category = db.Column(db.String(50))  # Lĩnh vực chuyên môn
    
    # ===== CHUYÊN GIA - THÔNG TIN CHUYÊN MÔN (THÊM MỚI) =====
    specialty = db.Column(db.String(100))              # Chuyên môn cụ thể
    experience_years = db.Column(db.Integer)           # Số năm kinh nghiệm
    workplace = db.Column(db.String(200))              # Nơi làm việc
    license_number = db.Column(db.String(100))         # Số chứng chỉ hành nghề
    license_expiry = db.Column(db.Date)                # Ngày hết hạn chứng chỉ
    consultation_fee = db.Column(db.Float)             # Phí tư vấn (VNĐ)
    education = db.Column(db.Text)                     # Học vấn
    certifications = db.Column(db.Text)                # Chứng chỉ (JSON string)
    availability = db.Column(db.String(20), default='available')  # available/busy/offline
    credibility_score = db.Column(db.Float, default=0) # Điểm uy tín

    # ===== RELATIONSHIPS =====
    posts = db.relationship('Post', backref='author', lazy='dynamic')

    # ===== PROPERTIES =====
    @property
    def avatar_url(self):
        if self.avatar and self.avatar != 'default.jpg':
            return url_for('static', filename=f'uploads/{self.avatar}')
        return url_for('static', filename='images/default-avatar.png')
    
    @property
    def friends(self):
        """Lấy danh sách bạn bè thực sự"""
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
    
    # ===== FRIENDSHIP METHODS =====
    def is_friends_with(self, user_id):
        return Friendship.query.filter(
            ((Friendship.user1_id == self.id) & (Friendship.user2_id == user_id)) |
            ((Friendship.user1_id == user_id) & (Friendship.user2_id == self.id))
        ).first() is not None
    
    def has_pending_friend_request_from(self, user_id):
        return FriendRequest.query.filter_by(
            sender_id=user_id, 
            receiver_id=self.id, 
            status='pending'
        ).first() is not None
    
    def has_pending_friend_request_to(self, user_id):
        return FriendRequest.query.filter_by(
            sender_id=self.id, 
            receiver_id=user_id, 
            status='pending'
        ).first() is not None
    
    def get_friendship_status(self, user_id):
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
        return FriendRequest.query.filter_by(
            receiver_id=self.id, 
            status='pending'
        ).order_by(FriendRequest.created_at.desc()).all()
    
    def get_sent_friend_requests(self):
        return FriendRequest.query.filter_by(
            sender_id=self.id, 
            status='pending'
        ).order_by(FriendRequest.created_at.desc()).all()

    # ===== EXPERT METHODS =====
    @property
    def can_request_expert(self):
        if self.is_verified_expert:
            return False
        
        pending = ExpertRequest.query.filter_by(
            user_id=self.id,
            status='pending'
        ).first()
        
        return pending is None

    def get_expert_progress(self):
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
    
    @property
    def is_expert(self):
        return self.is_verified_expert

# =====================================================
# POST MODEL
# =====================================================
class Post(db.Model):
    __tablename__ = 'posts' 
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    images = db.Column(db.Text)
    video = db.Column(db.String(200))
    category = db.Column(db.String(50), default='other')
    post_type = db.Column(db.String(20), default='question')
    is_expert_post = db.Column(db.Boolean, default=False)
    likes = db.Column(db.Integer, default=0)
    comments_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=vietnam_now)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_helpful = db.Column(db.Boolean, default=False)
    views = db.Column(db.Integer, default=0)
    rating = db.Column(db.Float, default=0.0)
    rating_count = db.Column(db.Integer, default=0)

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

# =====================================================
# POST LIKE MODEL
# =====================================================
class PostLike(db.Model):
    __tablename__ = 'post_like'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=vietnam_now)
    
    user = db.relationship('User', backref=db.backref('post_likes_rel', lazy='dynamic'))
    post = db.relationship('Post', backref='post_likes')
    
    __table_args__ = (db.UniqueConstraint('user_id', 'post_id', name='unique_post_like'),)

# =====================================================
# HIDDEN POST MODEL
# =====================================================
class HiddenPost(db.Model):
    __tablename__ = 'hidden_post'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=vietnam_now)
    
    __table_args__ = (db.UniqueConstraint('user_id', 'post_id', name='unique_hidden_post'),)

# =====================================================
# POST RATING MODEL
# =====================================================
class PostRating(db.Model):
    __tablename__ = 'post_rating'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    stars = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=vietnam_now)
    
    user = db.relationship('User', backref='post_ratings')
    post = db.relationship('Post', backref='post_ratings')
    
    __table_args__ = (db.UniqueConstraint('user_id', 'post_id', name='unique_post_rating'),)

# =====================================================
# EXPERT REQUEST MODEL
# =====================================================
class ExpertRequest(db.Model):
    __tablename__ = 'expert_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    certificate = db.Column(db.String(200))
    reason = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50))
    status = db.Column(db.String(20), default='pending')
    admin_note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=vietnam_now)
    updated_at = db.Column(db.DateTime, default=vietnam_now, onupdate=vietnam_now)
    
    user = db.relationship('User', backref='expert_requests')

# =====================================================
# COMMENT MODEL
# =====================================================
class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('comments.id'), nullable=True)
    
    image = db.Column(db.String(500), nullable=True)
    video = db.Column(db.String(500), nullable=True)
    sticker = db.Column(db.String(200), nullable=True)
    
    created_at = db.Column(db.DateTime, default=vietnam_now)
    updated_at = db.Column(db.DateTime, default=vietnam_now, onupdate=vietnam_now)
    is_edited = db.Column(db.Boolean, default=False)
    is_spam = db.Column(db.Boolean, default=False)
    
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

# =====================================================
# COMMENT LIKE MODEL
# =====================================================
class CommentLike(db.Model):
    __tablename__ = 'comment_likes'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    comment_id = db.Column(db.Integer, db.ForeignKey('comments.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=vietnam_now)
    
    __table_args__ = (db.UniqueConstraint('user_id', 'comment_id', name='unique_comment_like'),)

# =====================================================
# COMMENT REPORT MODEL
# =====================================================
class CommentReport(db.Model):
    __tablename__ = 'comment_reports'
    id = db.Column(db.Integer, primary_key=True)
    comment_id = db.Column(db.Integer, db.ForeignKey('comments.id'), nullable=False)
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reason = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=vietnam_now)
    
    reporter = db.relationship('User', backref='comment_reports')

# =====================================================
# NOTIFICATION MODEL
# =====================================================
class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(20))
    related_id = db.Column(db.Integer)
    related_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=vietnam_now)
    
    user = db.relationship('User', foreign_keys=[user_id], backref='notifications')
    related_user = db.relationship('User', foreign_keys=[related_user_id])

# =====================================================
# REPORT MODEL
# =====================================================
class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reason = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=vietnam_now)

    post = db.relationship('Post', backref='reports')
    user = db.relationship('User', backref='reports')

# =====================================================
# MESSAGE MODEL
# =====================================================
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

# =====================================================
# POINT HISTORY MODEL
# =====================================================
class PointHistory(db.Model):
    __tablename__ = 'point_history'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    points_change = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(255), nullable=False)
    related_id = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=vietnam_now)
    
    user = db.relationship('User', backref='point_history')

# =====================================================
# EXPERT PROFILE MODEL (TẠM GIỮ - CHƯA SỬ DỤNG)
# =====================================================
class ExpertProfile(db.Model):
    __tablename__ = 'expert_profiles'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    specialty = db.Column(db.String(100), nullable=False)
    license_number = db.Column(db.String(100))
    license_expiry = db.Column(db.Date)
    workplace = db.Column(db.String(200))
    experience_years = db.Column(db.Integer)
    education = db.Column(db.Text)
    certifications = db.Column(db.Text)
    availability = db.Column(db.String(100))
    consultation_fee = db.Column(db.Float)
    credibility_score = db.Column(db.Float, default=0)
    
    # expert_posts = db.relationship(
    #     'ExpertPost',
    #     back_populates='expert',
    #     lazy='dynamic',
    #     cascade='all, delete-orphan'
    # )

    # consultations = db.relationship(
    #     'Consultation',
    #     back_populates='expert',
    #     lazy='dynamic',
    #     cascade='all, delete-orphan'
    # )

# =====================================================
# EXPERT POST MODEL - BÀI VIẾT CHUYÊN GIA
# =====================================================
class ExpertPost(db.Model):
    __tablename__ = 'expert_posts'
    
    id = db.Column(db.Integer, primary_key=True)
    expert_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # Thay đổi từ expert_profile_id
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), default='other')
    medical_references = db.Column(db.Text)
    views_count = db.Column(db.Integer, default=0)
    likes_count = db.Column(db.Integer, default=0)
    comments_count = db.Column(db.Integer, default=0)
    is_published = db.Column(db.Boolean, default=False)
    published_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=vietnam_now)
    
    # Thay đổi relationship để trỏ đến User thay vì ExpertProfile
    expert = db.relationship('User', backref='expert_posts')

# =====================================================
# CONSULTATION MODEL - BUỔI TƯ VẤN
# =====================================================
class Consultation(db.Model):
    __tablename__ = 'consultations'
    
    id = db.Column(db.Integer, primary_key=True)
    expert_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    scheduled_at = db.Column(db.DateTime)
    duration_minutes = db.Column(db.Integer, default=30)
    max_participants = db.Column(db.Integer, default=1)
    status = db.Column(db.String(20), default="scheduled")
    notes = db.Column(db.Text)
    fee = db.Column(db.Float)
    
    # Sửa relationship để chỉ định rõ foreign_key
    expert = db.relationship('User', foreign_keys=[expert_id], backref='expert_consultations')
    user = db.relationship('User', foreign_keys=[user_id], backref='user_consultations')

# ✅ 1. KHUNG GIỜ - Chuyên gia tạo ra (Expert-owned slots)
class TimeSlot(db.Model):
    __tablename__ = 'time_slots'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # === CHUYÊN GIA SỞ HỮU ===
    expert_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # === THỜI GIAN ===
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    
    # === TRẠNG THÁI ===
    status = db.Column(db.String(20), default='available')  # available, booked, cancelled
    
    # === SỐ NGƯỜI TỐI ĐA ===
    max_participants = db.Column(db.Integer, default=1)
    
    # === GHI CHÚ ===
    notes = db.Column(db.Text)
    
    # === THỜI GIAN TẠO ===
    created_at = db.Column(db.DateTime, default=vietnam_now)
    
    # === RELATIONSHIPS ===
    expert = db.relationship('User', foreign_keys=[expert_id], backref='time_slots')
    booking = db.relationship('Booking', back_populates='time_slot', uselist=False)  # 1-1

# ✅ 2. ĐẶT LỊCH - Người dùng đặt vào khung giờ có sẵn
class Booking(db.Model):
    __tablename__ = 'bookings'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # === NGƯỜI ĐẶT ===
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # === KHUNG GIỜ ĐÃ CHỌN ===
    time_slot_id = db.Column(db.Integer, db.ForeignKey('time_slots.id'), nullable=False)
    
    # === NỘI DUNG YÊU CẦU ===
    notes = db.Column(db.Text)
    
    # === TRẠNG THÁI ===
    status = db.Column(db.String(20), default='scheduled')  # scheduled, completed, cancelled
    
    # === THỜI GIAN TẠO ===
    created_at = db.Column(db.DateTime, default=vietnam_now)
    
    # === RELATIONSHIPS ===
    user = db.relationship('User', foreign_keys=[user_id], backref='bookings')
    time_slot = db.relationship('TimeSlot', back_populates='booking')

# =====================================================
# EVENT LISTENERS
# =====================================================
@event.listens_for(db.session, 'before_flush')
def set_timestamps_before_flush(session, context, instances):
    for instance in session.new:
        if hasattr(instance, 'created_at') and instance.created_at is None:
            instance.created_at = vietnam_now()
        if hasattr(instance, 'updated_at'):
            instance.updated_at = vietnam_now()

    for instance in session.dirty:
        if hasattr(instance, 'updated_at'):
            instance.updated_at = vietnam_now()