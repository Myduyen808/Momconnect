# app.py
import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, make_response, abort, redirect, url_for, abort
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from flask_socketio import SocketIO, join_room, emit
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_migrate import Migrate
from database import db, init_app
from models import User, Post, Comment, Follow, FriendRequest, Notification, Report, ExpertRequest, Message, Friendship, vietnam_now, PostLike, HiddenPost, PostRating
from config import Config
import os
from datetime import datetime, timedelta
from sqlalchemy.orm import joinedload
from markupsafe import Markup
from sqlalchemy import func
import base64   
import time
import pytz
# Decorator kiểm tra quyền chuyên gia
from functools import wraps
from flask_login import current_user

# ✅ THÊM DÒNG NÀY - Import model CommentLike
from models import (
    db, 
    User, 
    Post, 
    Comment, 
    PostLike,           # ← Đổi từ 'Like' thành 'PostLike'
    PostRating,         # ← Đổi từ 'Rating' thành 'PostRating'
    Notification, 
    Message, 
    Friendship,         # ← Model bạn bè
    FriendRequest,      # ← Model lời mời kết bạn
    Report, 
    CommentLike,        # ← Model like comment
    CommentReport,      # ← Model báo cáo comment
    ExpertRequest,      # ← Thêm cái này nếu dùng
    Follow,             # ← Thêm cái này nếu dùng
    HiddenPost,          # ← Thêm cái này nếu dùng
    ExpertProfile,
    TimeSlot,      # ← Add this
    Booking,       # ← Add this
    ExpertPost 
)


# Trong file app.py hoặc routes.py
from notification_service import NotificationService
from notifications_api import notifications_api

# ========================
# TẠO APP VÀ CẤU HÌNH
# ========================

app = Flask(__name__)   
app.config.from_object(Config)

app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=7)
app.config['JSON_AS_ASCII'] = False  # Giữ nguyên ký tự Unicode (tiếng Việt có dấu)

# ========================
# KHỞI TẠO DB TRONG CONTEXT (CHỈ 1 LẦN)
# ========================
with app.app_context():
    init_app(app)  # Khởi tạo db với app

# KHÔNG GỌI db.create_all() Ở ĐÂY NỮA – ĐỂ FLASK-MIGRATE QUẢN LÝ!

# ========================
# KHỞI TẠO CÁC EXTENSION
# ========================
migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

socketio = SocketIO(app, 
                    cors_allowed_origins="*", 
                    async_mode='eventlet',
                    logger=True, 
                    engineio_logger=True)

# ========================
# USER LOADER
# ========================
@login_manager.user_loader
def load_user(id):
    user = User.query.get(int(id))
    if user:
        update_user_badge(user)  # ← Tự động cập nhật badge mỗi khi đăng nhập/load user
    return user

# ========================
# UPLOAD FOLDER
# ========================
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ===== THÊM ĐOẠN CODE NÀY =====
@app.template_filter('vietnam_time')
def vietnam_time_filter(dt):
    """Filter để định dạng datetime object sang giờ Việt Nam."""
    if dt is None:
        return ""
    
    # ✅ NẾU DATETIME ĐÃ CÓ TIMEZONE → CONVERT SANG VN
    if dt.tzinfo is not None:
        dt = dt.astimezone(pytz.timezone('Asia/Ho_Chi_Minh'))
    # ✅ NẾU DATETIME NAIVE → COI NHƯ ĐÃ LÀ GIỜ VN (KHÔNG CONVERT)
    
    return dt.strftime('%H:%M %d/%m/%Y')

# === HÀM HỖ TRỢ ===
def get_friends(user):
    """Lấy danh sách bạn bè (đã chấp nhận lời mời)"""
    friendships = Friendship.query.filter(
        (Friendship.user1_id == user.id) | (Friendship.user2_id == user.id)
    ).all()
    
    friend_ids = []
    for friendship in friendships:
        if friendship.user1_id == user.id:
            friend_ids.append(friendship.user2_id)
        else:
            friend_ids.append(friendship.user1_id)
    
    return User.query.filter(User.id.in_(friend_ids)).all()

def get_suggested_users(user):
    follows = Follow.query.filter_by(follower_id=user.id).all()
    suggested = [f.followed_id for f in follows if not Follow.query.filter_by(follower_id=f.followed_id, followed_id=user.id).first()]
    return User.query.filter(User.id.in_(suggested)).all()

def is_friend(user1_id, user2_id):
    f1 = Follow.query.filter_by(follower_id=user1_id, followed_id=user2_id).first()
    f2 = Follow.query.filter_by(follower_id=user2_id, followed_id=user1_id).first()
    return bool(f1 and f2)

# === HÀM CẬP NHẬT CẤP BẬC (BADGE) THEO ĐIỂM ===
def update_user_badge(user):
    old_badge = getattr(user, 'badge', None)
    points = user.points
    
    if points > 2000:
        badge = "Ứng viên Chuyên gia 🌟"
        can_request_expert = True
    elif points >= 1001:
        badge = "Thành Viên Bạc 🥈"
        can_request_expert = False
    elif points >= 201:
        badge = "Thành Viên Đồng 🥉"
        can_request_expert = False
    else:
        badge = "Mầm Non 👶"
        can_request_expert = False

    # Cập nhật badge
    if old_badge != badge:
        user.badge = badge
        db.session.commit()
        
        # Gửi thông báo khi lên cấp
        notif = Notification(
            user_id=user.id,
            title="Chúc mừng bạn đã lên cấp!",
            message=f"Bạn đã đạt cấp bậc {badge}. Tiếp tục phát huy nhé!",
            type='level_up'
        )
        db.session.add(notif)
        # db.session.commit()
    
def notify_all_admins(title, message, type='system', related_user_id=None, related_id=None):
    """Gửi thông báo đến tất cả Admin"""
    admins = User.query.filter_by(role='admin').all()
    for admin in admins:
        notif = Notification(
            user_id=admin.id,
            title=title,
            message=message,
            type=type,
            related_user_id=related_user_id,
            related_id=related_id
        )
        db.session.add(notif)
    db.session.commit()

# === TRANG CHỦ ===
@app.route('/')
def home():
    category = request.args.get('category', 'all')
    query = Post.query
    
    # Lọc bỏ các bài đã ẩn
    if current_user.is_authenticated:
        hidden_post_ids = [h.post_id for h in HiddenPost.query.filter_by(user_id=current_user.id).all()]
        if hidden_post_ids:
            query = query.filter(~Post.id.in_(hidden_post_ids))
    
    query = query.order_by(Post.created_at.desc())
    
    if category != 'all':
        query = query.filter_by(category=category)
    
    posts = query.limit(20).all()

    # Thêm thông tin like cho mỗi bài
    for post in posts:
        if current_user.is_authenticated:
            post.is_liked_by_user = PostLike.query.filter_by(
                user_id=current_user.id, 
                post_id=post.id
            ).first() is not None
            
            # Lấy danh sách người thích (top 3)
            post.likers = [like.user for like in PostLike.query.filter_by(post_id=post.id).limit(3).all()]
        else:
            post.is_liked_by_user = False
            post.likers = []
        
        # Đảm bảo có giá trị views
        if not hasattr(post, 'views') or post.views is None:
            post.views = 0

    categories = ['all', 'health', 'nutrition', 'story', 'tips', 'other']
    category_names = {
        'all': 'Tất cả', 'health': 'Sức khỏe', 'nutrition': 'Dinh dưỡng',
        'story': 'Tâm sự', 'tips': 'Mẹo hay', 'other': 'Khác'
    }

    # Sử dụng cùng hàm với trang bạn bè
    friends = get_friends(current_user) if current_user.is_authenticated else []
    suggested_users = get_suggested_users(current_user, limit=5) if current_user.is_authenticated else []

    return render_template(
        'home.html', posts=posts, selected_category=category,
        categories=categories, category_names=category_names,
        friends=friends, suggested_users=suggested_users
    )

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip()
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            
            # Lưu thông tin chuyên gia vào session
            session['is_expert'] = user.is_verified_expert
            if user.is_verified_expert:
                session['expert_category'] = user.expert_category
            
            return redirect(url_for('home'))
        
        flash('Email hoặc mật khẩu sai!', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


# Decorator kiểm tra quyền chuyên gia
def expert_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_verified_expert:
            flash('Chỉ chuyên gia mới được truy cập tính năng này!', 'error')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

# LIKE
@app.route('/like/<int:post_id>', methods=['POST'])
@login_required
def like(post_id):
    post = Post.query.get_or_404(post_id)
    
    # Kiểm tra đã like chưa
    existing_like = PostLike.query.filter_by(
        user_id=current_user.id,
        post_id=post_id
    ).first()
    
    if existing_like:
        # Unlike
        db.session.delete(existing_like)
        post.likes -= 1
        
        # Giảm 10 điểm của chủ bài
        post.author.points = max(0, post.author.points - 10)
        update_user_badge(post.author)
        liked = False
    else:
        # Like
        new_like = PostLike(user_id=current_user.id, post_id=post_id)
        db.session.add(new_like)
        post.likes += 1
        liked = True

        # === CỘNG 10 ĐIỂM CHO CHỦ BÀI KHI NHẬN LIKE ===
        post.author.points += 10
        update_user_badge(post.author)
        
        # Tạo thông báo
        if post.author.id != current_user.id:
            notif = Notification(
                user_id=post.author.id,
                title="Có lượt thích mới!",
                message=f"{current_user.name} đã thích bài viết của bạn.",
                type='like',
                related_id=post.id,
                related_user_id=current_user.id
            )
            db.session.add(notif)   

    db.session.commit()
    
    # Lấy danh sách người thích (top 3)
    likers = [like.user.name for like in PostLike.query.filter_by(post_id=post_id).limit(3).all()]
    
    return jsonify({
        'likes': post.likes,
        'points': current_user.points,
        'liked': liked,
        'likers': likers,
        'total_likers': PostLike.query.filter_by(post_id=post_id).count()
    })

# COMMENT
# Thêm vào app.py

# 🔥 GỬI BÌNH LUẬN VỚI MEDIA
@app.route('/comment/<int:post_id>', methods=['POST'])
@login_required
def comment(post_id):
    post = Post.query.get_or_404(post_id)
    content = request.form.get('content', '').strip()
    parent_id = request.form.get('parent_id')
    
    # Xử lý media
    image_file = None
    video_file = None
    sticker = request.form.get('sticker')
    
    if 'media' in request.files:
        file = request.files['media']
        if file and file.filename:
            filename = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            if file.mimetype.startswith('video'):
                video_file = filename
            else:
                image_file = filename
    
    if not content and not image_file and not video_file and not sticker:
        return jsonify({'error': 'Nội dung trống!'}), 400
    
    comment_obj = Comment(
        content=content,
        user_id=current_user.id,
        post_id=post_id,
        parent_id=parent_id,
        image=image_file,
        video=video_file,
        sticker=sticker
    )
    
    db.session.add(comment_obj)
    post.comments_count += 1

    # === CỘNG 5 ĐIỂM KHI BÌNH LUẬN ===
    current_user.points += 5
    update_user_badge(current_user)
    
    # Thông báo cho chủ bài viết
    if post.author.id != current_user.id:
        notif = Notification(
            user_id=post.author.id,
            title="Bình luận mới",
            message=f"{current_user.name} đã bình luận: {content[:50] if content else '[Media]'}",
            type='comment',
            related_id=post.id,
            related_user_id=current_user.id
        )
        db.session.add(notif)
    
    # Thông báo nếu là reply
    if parent_id:
        parent_comment = Comment.query.get(parent_id)
        if parent_comment and parent_comment.user_id != current_user.id:
            notif = Notification(
                user_id=parent_comment.user_id,
                title="Phản hồi bình luận",
                message=f"{current_user.name} đã trả lời bình luận của bạn",
                type='comment_reply',
                related_id=post.id,
                related_user_id=current_user.id
            )
            db.session.add(notif)
    
    db.session.commit()
    
    # Trả về comment với đầy đủ thông tin
    return jsonify({
        'success': True,
        'comment': {
            'id': comment_obj.id,
            'content': comment_obj.content,
            'author': {
                'id': current_user.id,
                'name': current_user.name,
                'avatar': current_user.avatar or 'images/default-avatar.png'
            },
            'image': f'uploads/{image_file}' if image_file else None,
            'video': f'uploads/{video_file}' if video_file else None,
            'sticker': sticker,
            'created_at': 'Vừa xong',
            'likes_count': 0,
            'is_liked': False,
            'can_edit': True,
            'can_delete': True,
            'replies': []
        }
    })

# 🔥 SỬA BÌNH LUẬN
@app.route('/api/comment/<int:comment_id>/edit', methods=['POST'])
@login_required
def edit_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    
    if not comment.can_edit(current_user):
        return jsonify({'error': 'Không có quyền chỉnh sửa!'}), 403
    
    data = request.get_json()
    new_content = data.get('content', '').strip()
    
    if not new_content:
        return jsonify({'error': 'Nội dung không được để trống!'}), 400
    
    comment.content = new_content
    comment.is_edited = True
    comment.updated_at = vietnam_now()
    
    db.session.commit()
    return jsonify({'success': True, 'content': new_content})

# 🔥 XÓA BÌNH LUẬN
@app.route('/api/comment/<int:comment_id>/delete', methods=['POST'])
@login_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    
    if not comment.can_delete(current_user):
        return jsonify({'error': 'Không có quyền xóa!'}), 403
    
    post = comment.post
    
    # Đếm tổng số replies để trừ đúng
    def count_all_replies(c):
        count = c.replies.count()
        for reply in c.replies:
            count += count_all_replies(reply)
        return count
    
    total_deleted = 1 + count_all_replies(comment)
    post.comments_count = max(0, post.comments_count - total_deleted)
    
    db.session.delete(comment)
    db.session.commit()
    
    return jsonify({'success': True})

# 🔥 LIKE COMMENT
@app.route('/api/comment/<int:comment_id>/like', methods=['POST'])
@login_required
def like_comment(comment_id):
    try:
        comment = Comment.query.get_or_404(comment_id)
        
        existing = CommentLike.query.filter_by(
            user_id=current_user.id,
            comment_id=comment_id
        ).first()
        
        if existing:
            db.session.delete(existing)
            db.session.commit()
            liked = False
        else:
            like = CommentLike(user_id=current_user.id, comment_id=comment_id)
            db.session.add(like)
            db.session.commit()
            liked = True
            
            # Thông báo (optional)
            if comment.user_id != current_user.id:
                notif = Notification(
                    user_id=comment.user_id,
                    title="Thích bình luận",
                    message=f"{current_user.name} đã thích bình luận của bạn",
                    type='comment_like',
                    related_id=comment.post_id,
                    related_user_id=current_user.id
                )
                db.session.add(notif)
                db.session.commit()
        
        return jsonify({
            'success': True,
            'liked': liked,
            'likes': comment.likes_count
        })
    except Exception as e:
        print(f"Error in like_comment: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

# 🔥 BÁO CÁO BÌNH LUẬN SPAM
@app.route('/api/comment/<int:comment_id>/report', methods=['POST'])
@login_required
def report_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    data = request.get_json()
    reason = data.get('reason', '').strip()
    
    if not reason:
        return jsonify({'error': 'Vui lòng nhập lý do!'}), 400

    existing = CommentReport.query.filter_by(comment_id=comment_id, reporter_id=current_user.id).first()
    if existing:
        return jsonify({'error': 'Bạn đã báo cáo rồi!'}), 400

    report = CommentReport(comment_id=comment_id, reporter_id=current_user.id, reason=reason)
    db.session.add(report)
    
    if comment.reports.count() + 1 >= 3:
        comment.is_spam = True
    
    db.session.commit()

    # THÔNG BÁO CHO ADMIN
    notify_all_admins(
        title="Báo cáo bình luận mới!",
        message=f"{current_user.name} báo cáo bình luận của {comment.author.name} trong bài '{comment.post.title[:40]}...' - Lý do: {reason}",
        type='report_comment',
        related_user_id=current_user.id,
        related_id=comment.post.id
    )

    return jsonify({'success': True})

# 🔥 API LẤY COMMENTS (nested) - SỬA LẠI
@app.route('/comments/<int:post_id>')
def get_comments(post_id):
    # Lấy tất cả bình luận không bị đánh dấu spam
    comments = Comment.query.filter_by(
        post_id=post_id, 
        parent_id=None,
        is_spam=False
    ).order_by(Comment.created_at.desc()).all()
    
    def serialize_comment(c):
        # Lấy danh sách replies
        replies_data = []
        for reply in c.replies.filter_by(is_spam=False).order_by(Comment.created_at.asc()):
            replies_data.append(serialize_comment(reply))
        
        # Lấy thông tin author
        author_avatar = c.author.avatar or 'images/default-avatar.png'
        if not author_avatar.startswith('uploads/'):
            author_avatar = f'uploads/{author_avatar}' if not author_avatar.startswith('static/') else author_avatar.replace('static/', '')
        
        # Lấy thông tin media
        image = None
        video = None
        if c.image:
            image = f'uploads/{c.image}'
        elif c.video:
            video = f'uploads/{c.video}'
        
        return {
            'id': c.id,
            'content': c.content,
            'author': {
                'id': c.author.id,
                'name': c.author.name,
                'avatar': author_avatar
            },
            'image': image,
            'video': video,
            'sticker': c.sticker,
            'is_edited': c.is_edited,
            'created_at': c.created_at.strftime('%H:%M %d/%m/%Y'),
            'likes': c.likes_count,
            'is_liked': c.is_liked_by(current_user.id) if current_user.is_authenticated else False,
            'can_edit': c.can_edit(current_user) if current_user.is_authenticated else False,
            'can_delete': c.can_delete(current_user) if current_user.is_authenticated else False,
            'replies': replies_data
        }
    
    return jsonify([serialize_comment(c) for c in comments])


# 🔥 TÌM KIẾM USER CHO MENTION
@app.route('/api/users/search')
@login_required
def search_users():
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify([])
    
    users = User.query.filter(
        User.name.ilike(f'%{query}%')
    ).limit(10).all()
    
    return jsonify([{
        'id': u.id,
        'name': u.name,
        'avatar': u.avatar or 'images/default-avatar.png'
    } for u in users])


from sqlalchemy import func

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        current_user.name = request.form['name'].strip()
        current_user.bio = request.form.get('bio', '').strip()
        
        # ✅ THÊM 2 DÒNG NÀY
        current_user.children_count = int(request.form.get('children_count', 0))
        current_user.children_ages = request.form.get('children_ages', '').strip()
        
        if 'avatar' in request.files:
            file = request.files['avatar']
            if file and file.filename:
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                current_user.avatar = f'uploads/{filename}'
        
        db.session.commit()
        flash('Cập nhật hồ sơ thành công!', 'success')
        return redirect(url_for('profile'))
    
    # Tính toán thống kê
    total_posts = current_user.posts.count()
    total_comments = Comment.query.filter_by(user_id=current_user.id).count()

    # Tính trung bình like (nếu có bài viết)
    avg_likes = 0
    if total_posts > 0:
        avg_result = db.session.query(func.avg(Post.likes))\
                              .filter(Post.user_id == current_user.id)\
                              .scalar()
        avg_likes = round(avg_result or 0, 1)

    return render_template(
        'profile.html',
        user=current_user,
        Comment=Comment,
        total_posts=total_posts,
        total_comments=total_comments,
        avg_likes=avg_likes   # ← Truyền số đã tính, không cần db
    )

# ĐĂNG BÀI
@app.route('/post', methods=['GET', 'POST'])
@login_required
def create_post():
    if request.method == 'POST':
        title = request.form.get('title').strip()
        content = request.form.get('content').strip()
        category = request.form.get('category', 'other')
        post_type = request.form.get('post_type', 'question')  # Lấy loại bài
        
        # Kiểm tra xem người dùng có phải là chuyên gia và có đăng bài chuyên gia không
        is_expert_post = current_user.is_verified_expert and request.form.get('is_expert_post') == 'on'
        
        images_list = []
        video_file = None

        if 'media' in request.files:
            files = request.files.getlist('media')
            for file in files:
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(filepath)
                    if file.mimetype.startswith('video/'):
                        video_file = filename
                    else:
                        images_list.append(filename)

        post = Post(
            title=title,
            content=content,
            category=category,
            images=','.join(images_list) if images_list else None,
            video=video_file,
            user_id=current_user.id,
            post_type=post_type,  # ← Gán loại bài
            is_expert_post=is_expert_post  # ← Đánh dấu bài viết chuyên gia
        )
        
        post.created_at = vietnam_now()
        db.session.add(post)
        db.session.commit()

        # Thông báo cho tác giả nếu là bài viết chuyên gia
        if is_expert_post:
            # Thông báo cho tất cả người theo dõi (follower) của chuyên gia
            followers = Follow.query.filter_by(followed_id=current_user.id).all()
            
            for follower in followers:
                # Kiểm tra xem đã có thông báo tương tự chưa (tránh spam)
                existing_notif = Notification.query.filter_by(
                    user_id=follower.follower_id,  # follower.follower_id là người nhận
                    type='expert_post',
                    related_id=post.id
                ).first()
                
                if not existing_notif:
                    new_notif = Notification(
                        user_id=follower.follower_id,
                        title="Bài viết tư vấn mới từ chuyên gia",
                        message=f"{current_user.name} vừa đăng bài tư vấn mới trong lĩnh vực {current_user.expert_category or 'của bạn'}.",
                        type='expert_post',
                        related_id=post.id,
                        related_user_id=current_user.id
                    )
                    db.session.add(new_notif)
            
            db.session.commit()  # Commit sau khi thêm tất cả thông báo
            flash('Bài viết tư vấn đã được đăng thành công và thông báo cho người theo dõi!', 'success')
        else:
            flash('Bài viết đã được đăng thành công!', 'success')

        return redirect(url_for('home'))

    # 🔥 THÊM DÒNG NÀY: XỬ LÝ KHI MỞ TRANG ĐĂNG BÀI (GET)
    return render_template('post.html')

# ĐĂNG KÝ
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name'].strip()
        email = request.form['email'].strip().lower()
        password = request.form['password']
        confirm = request.form['confirm_password']

        if len(password) < 6:
            flash('Mật khẩu phải có ít nhất 6 ký tự!', 'danger')
            return render_template('register.html')
        if password != confirm:
            flash('Mật khẩu xác nhận không khớp!', 'danger')
            return render_template('register.html')
        if User.query.filter_by(email=email).first():
            flash('Email đã được sử dụng!', 'danger')
            return render_template('register.html')

        hashed = generate_password_hash(password)
        user = User(name=name, email=email, password=hashed, points=10)
        db.session.add(user)
        db.session.commit()

        # Thông báo cho admin
        notify_all_admins(
            title="Thành viên mới đăng ký!",
            message=f"Người dùng mới: {name} ({email}) vừa đăng ký tài khoản.",
            type='new_user',
            related_user_id=user.id
        )
        
        flash('Đăng ký thành công! Hãy đăng nhập.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/follow/<int:user_id>', methods=['POST'])
@login_required
def follow_user(user_id):
    target_user = User.query.get_or_404(user_id)
    
    if target_user.id == current_user.id:
        return jsonify({'error': 'Không thể theo dõi chính mình!'}), 400
    
    # Kiểm tra đã theo dõi chưa
    is_following = current_user.following.filter_by(followed_id=target_user.id).first()
    
    if request.json.get('action') == 'unfollow' or is_following:
        # Bỏ theo dõi
        if is_following:
            current_user.following.remove(is_following)
            message = 'Đã bỏ theo dõi!'
        else:
            message = 'Chưa theo dõi người này!'
    else:
        # Theo dõi mới
        follow = Follow(
            follower_id=current_user.id,
            followed_id=target_user.id
        )
        db.session.add(follow)
        message = 'Đã theo dõi!'
    
    db.session.commit()
    return jsonify({
        'following': not bool(is_following),
        'message': message
    })

from sqlalchemy import not_, and_, exists

def get_pending_requests(user):
    """Lấy danh sách lời mời kết bạn đang chờ xử lý"""
    return FriendRequest.query.filter_by(
        receiver_id=user.id, 
        status='pending'
    ).order_by(FriendRequest.created_at.desc()).all()

def get_sent_requests(user):
    """Lấy danh sách lời mời đã gửi"""
    return FriendRequest.query.filter_by(
        sender_id=user.id, 
        status='pending'
    ).order_by(FriendRequest.created_at.desc()).all()

def get_suggested_users(user, limit=5):
    """Lấy danh sách gợi ý kết bạn"""
    # Lấy ID của bạn bè và của chính user
    friend_ids = [f.id for f in get_friends(user)] + [user.id]
    
    # Lấy ID của những người đã gửi hoặc nhận lời mời
    pending_ids = []
    for req in get_pending_requests(user):
        pending_ids.append(req.sender_id)
    for req in get_sent_requests(user):
        pending_ids.append(req.receiver_id)
    
    # Loại trừ tất cả những người trên
    excluded_ids = friend_ids + pending_ids
    
    # Lấy ngẫu nhiên những người còn lại
    return User.query.filter(
        ~User.id.in_(excluded_ids)
    ).order_by(func.random()).limit(limit).all()    

@app.route('/notifications')
@login_required
def notifications():
    user_id = current_user.id
    Notification.query.filter_by(user_id=user_id, is_read=False).update({'is_read': True})
    db.session.commit()
    notifications_list = (Notification.query
                          .filter_by(user_id=user_id)
                          .order_by(Notification.created_at.desc())
                          .all())
    return render_template('notifications.html', notifications=notifications_list)

@app.route('/api/notifications')
@login_required
def api_notifications():
    notifs = (Notification.query
        .filter_by(user_id=current_user.id)
        .options(joinedload(Notification.related_user))
        .order_by(Notification.created_at.desc())
        .limit(10)
        .all())
    
    results = []
    for n in notifs:
        avatar = n.related_user.avatar if n.related_user and n.related_user.avatar else 'images/default-avatar.png'
        if not avatar.startswith('uploads/'):
            avatar = f'uploads/{avatar}' if not avatar.startswith('static/') else avatar.replace('static/', '')
        avatar_url = url_for('static', filename=avatar)
        
        # 🔥 TẠO redirect_url với hash để scroll
        redirect_url = '/notifications'
        
        if n.type == 'comment' and n.related_id:
            redirect_url = f'/post/{n.related_id}#comments-section-{n.related_id}'
        elif n.type == 'like' and n.related_id:
            redirect_url = f'/post/{n.related_id}'
        elif n.type in ['friend_request', 'friend_accepted']:
            redirect_url = f'/notifications#notif-{n.id}'  # 🔥 SCROLL TỚI THÔNG BÁO
        else:
            redirect_url = f'/notifications#notif-{n.id}'  # 🔥 MẶC ĐỊNH
        
        results.append({
            "id": n.id,
            "title": n.title,
            "message": n.message[:60] + '...' if len(n.message) > 60 else n.message,
            "type": n.type,
            "is_read": n.is_read,
            "created_at": n.created_at.strftime('%H:%M %d/%m'),
            "related_user_avatar": avatar_url,
            "redirect_url": redirect_url  # 🔥 ĐÃ CÓ HASH
        })
    
    return jsonify(results)


@app.route('/notifications/count')
@login_required
def notification_count():
    count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return jsonify({'count': count})


@app.route('/api/notifications/<int:notif_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notif_id):
    notif = Notification.query.get_or_404(notif_id)
    
    # Check quyền
    if notif.user_id != current_user.id:
        return jsonify({'error': 'Không có quyền'}), 403
    
    notif.is_read = True
    db.session.commit()
    
    return jsonify({'success': True})

# app.py – THÊM ROUTE NÀY
@app.route('/post/<int:post_id>')
def post_detail(post_id):
    post = Post.query.get_or_404(post_id)
    
    # Tăng thêm 1 lượt xem khi người dùng xem chi tiết
    # Kiểm tra xem người dùng đã xem bài viết này trong phiên hiện tại chưa
    if current_user.is_authenticated:
        # Lấy danh sách các bài viết đã xem chi tiết trong phiên của người dùng
        detail_viewed_posts = session.get('detail_viewed_posts', [])
        
        # Chỉ tăng lượt xem nếu người dùng không phải là tác giả và chưa xem bài viết này trong phiên hiện tại
        if current_user.id != post.user_id and post_id not in detail_viewed_posts:
            post.views += 1  # Tăng thêm 1 lượt xem
            db.session.commit()
            
            # Thêm bài viết vào danh sách đã xem chi tiết
            detail_viewed_posts.append(post_id)
            session['detail_viewed_posts'] = detail_viewed_posts
    else:
        # Đối với người dùng chưa đăng nhập, sử dụng cookie để theo dõi
        detail_viewed_posts = request.cookies.get('detail_viewed_posts', '').split(',')
        detail_viewed_posts = [int(p) for p in detail_viewed_posts if p.isdigit()]
        
        if post_id not in detail_viewed_posts:
            post.views += 1  # Tăng thêm 1 lượt xem
            db.session.commit()
            
            # Thêm bài viết vào cookie
            detail_viewed_posts.append(post_id)
            response = make_response(render_template('post_detail.html', post=post, comments=comments))
            response.set_cookie('detail_viewed_posts', ','.join(map(str, detail_viewed_posts)), max_age=3600) # 1 giờ
            return response
    
    comments = Comment.query.filter_by(post_id=post_id).order_by(Comment.created_at.desc()).all()
    return render_template('post_detail.html', post=post, comments=comments)

# app.py – THÊM ROUTE TÌM KIẾM
@app.route('/search')
def search():
    query = request.args.get('q', '').strip()
    if not query:
        return render_template('search.html', query='', posts=[], users=[])

    # Tìm bài viết (tiêu đề + nội dung)
    posts = Post.query.filter(
        db.or_(
            Post.title.ilike(f'%{query}%'),
            Post.content.ilike(f'%{query}%')
        )
    ).order_by(Post.created_at.desc()).limit(20).all()

    # Tìm người dùng
    users = User.query.filter(
        User.name.ilike(f'%{query}%')
    ).limit(10).all()

    return render_template('search.html', query=query, posts=posts, users=users)

# app.py – THÊM VÀO ĐẦU FILE (SAU CÁC IMPORT)
from flask import jsonify, request
from models import Report  # THÊM DÒNG NÀY

@app.route('/report/<int:post_id>', methods=['POST'])
@login_required
def report_post(post_id):
    post = Post.query.get_or_404(post_id)
    
    reason = request.form.get('reason', '').strip()
    if not reason:
        return jsonify({'error': 'Vui lòng chọn lý do!'}), 400

    existing = Report.query.filter_by(post_id=post_id, user_id=current_user.id).first()
    if existing:
        return jsonify({'error': 'Bạn đã báo cáo bài viết này rồi!'}), 400

    report = Report(post_id=post_id, user_id=current_user.id, reason=reason)
    db.session.add(report)
    db.session.commit()

    # THÊM THÔNG BÁO CHO ADMIN
    notify_all_admins(
        title="Báo cáo bài viết mới!",
        message=f"Người dùng {current_user.name} báo cáo bài viết: '{post.title[:50]}...' - Lý do: {reason}",
        type='report_post',
        related_user_id=current_user.id,
        related_id=post.id
    )

    return jsonify({'success': True, 'message': 'Đã gửi báo cáo thành công!'})

# app.py
from flask_login import current_user

# app.py
@app.route('/verify/<int:post_id>', methods=['POST'])
@login_required
def verify_post(post_id):
    if current_user.role != 'expert':
        return jsonify({'error': 'Không có quyền!'}), 403
    post = Post.query.get_or_404(post_id)
    post.is_verified = True
    post.verified_by = current_user.id
    db.session.commit()
    return jsonify({'success': True})

@app.route('/expert/post', methods=['GET', 'POST'])
@login_required
def expert_post():
    if not current_user.is_verified_expert:
        flash('Chỉ chuyên gia mới được đăng!', 'error')
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        post = Post(
            title=request.form['title'].strip(),
            content=request.form['content'].strip(),
            category=request.form.get('category', 'other'),
            is_expert_post=True,
            user_id=current_user.id
            # ĐÃ XÓA expert_id vì không còn cột này nữa!
        )
        db.session.add(post)
        db.session.commit()
        flash('Đăng bài tư vấn thành công!', 'success')
        return redirect(url_for('home'))
    
    return render_template('expert_post.html')

# app.py – THÊM VÀO PHẦN ROUTES

@app.route('/expert/request', methods=['GET', 'POST'])
@login_required
def expert_request():
    # ✅ ĐÃ LÀ CHUYÊN GIA
    if current_user.is_verified_expert:
        flash('Bạn đã là chuyên gia!', 'info')
        return redirect(url_for('home'))
    
    # ✅ KIỂM TRA ĐÃ CÓ YÊU CẦU PENDING
    pending_request = ExpertRequest.query.filter_by(
        user_id=current_user.id,
        status='pending'
    ).first()
    
    if pending_request:
        flash('Bạn đã gửi yêu cầu trước đó. Vui lòng chờ admin duyệt!', 'warning')
        return redirect(url_for('profile'))
    
    # ✅ BỎ KIỂM TRA ĐIỀU KIỆN ĐIỂM - AI CŨNG ĐƯỢC GỬI
    if request.method == 'POST':
        reason = request.form.get('reason', '').strip()
        category = request.form.get('category')
        file = request.files.get('certificate')

        if not reason or not category:
            flash('Vui lòng điền đầy đủ thông tin!', 'danger')
            return render_template('expert_request.html')

        # Xử lý upload ảnh chứng chỉ
        filename = None
        if file and file.filename:
            filename = secure_filename(f"{current_user.id}_{int(time.time())}_{file.filename}")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            filename = f'uploads/{filename}'
        else:
            flash('Vui lòng tải lên ảnh chứng chỉ!', 'danger')
            return render_template('expert_request.html')

        # Tạo yêu cầu
        req = ExpertRequest(
            user_id=current_user.id,
            reason=reason,
            category=category,
            certificate=filename,
            status='pending'
        )
        db.session.add(req)
        
        # Thông báo cho admin
        notify_all_admins(
            title="Yêu cầu chuyên gia mới!",
            message=f"{current_user.name} đã nộp đơn trở thành chuyên gia",
            type='expert_request',
            related_user_id=current_user.id
        )
        
        db.session.commit()
        flash('Đã gửi yêu cầu! Admin sẽ xem xét trong 3-5 ngày.', 'success')
        return redirect(url_for('profile'))

    return render_template('expert_request.html')

@app.route('/admin/user/<int:user_id>/<action>', methods=['GET', 'POST'])
@login_required
def admin_user_action(user_id, action):
    if current_user.role != 'admin':
        flash('Bạn không có quyền!', 'error')
        return redirect(url_for('home'))

    user = User.query.get_or_404(user_id)

    if action == 'block':
        user.is_active = False
        flash(f'Đã khóa tài khoản {user.name}', 'success')
    elif action == 'unblock':
        user.is_active = True
        flash(f'Đã mở khóa tài khoản {user.name}', 'success')
    else:
        flash('Hành động không hợp lệ!', 'error')
        return redirect(url_for('admin_dashboard'))

    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/expert/<int:req_id>/<action>', methods=['POST'])
@login_required
def admin_expert_action(req_id, action):
    if current_user.role != 'admin':
        return jsonify({'error': 'Không có quyền!'}), 403

    req = ExpertRequest.query.get_or_404(req_id)
    
    if action == 'approve':
        # LỚP 2: Admin đã kiểm tra thủ công
        req.user.is_verified_expert = True
        req.user.expert_category = req.category
        req.user.points += 500  # Thưởng lớn
        req.status = 'approved'
        req.admin_note = request.form.get('note', 'Đã phê duyệt')
        
        # Thông báo cho user
        notif = Notification(
            user_id=req.user_id,
            title="🎉 Chúc mừng! Bạn đã trở thành Chuyên gia",
            message=f"Tài khoản của bạn đã được nâng cấp thành Chuyên gia lĩnh vực {req.category}. Bạn nhận được 500 điểm thưởng!",
            type='expert_approved',
            related_user_id=current_user.id
        )
        db.session.add(notif)
        flash(f'Đã duyệt chuyên gia: {req.user.name}', 'success')
        
    elif action == 'reject':
        req.status = 'rejected'
        req.admin_note = request.form.get('note', 'Không đạt yêu cầu')
        
        # Thông báo từ chối
        notif = Notification(
            user_id=req.user_id,
            title="Yêu cầu chuyên gia không được chấp nhận",
            message=f"Lý do: {req.admin_note}. Bạn có thể nộp lại sau khi cải thiện hồ sơ.",
            type='expert_rejected'
        )
        db.session.add(notif)
        flash(f'Đã từ chối: {req.user.name}', 'info')
    
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/user/edit', methods=['POST'])
@login_required
def admin_edit_user():
    if current_user.role != 'admin':
        return jsonify({'error': 'Không có quyền!'}), 403

    try:
        user_id = request.form.get('user_id')
        user = User.query.get_or_404(user_id)

        if user.id == current_user.id:
            return jsonify({'error': 'Không thể chỉnh sửa tài khoản admin hiện tại!'}), 400

        user.name = request.form.get('name', user.name).strip()
        user.email = request.form.get('email', user.email).strip().lower()
        user.role = request.form.get('role', user.role)
        user.points = int(request.form.get('points', user.points))

        # Xử lý avatar mới
        if 'avatar' in request.files:
            file = request.files['avatar']
            if file and file.filename:
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                user.avatar = f"uploads/{filename}"

        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error editing user: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ---------- QUẢN LÝ BÀI VIẾT ----------
@app.route('/admin/post/<int:post_id>/comments')
@login_required
def admin_post_comments(post_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Không có quyền'}), 403
    
    post = Post.query.get_or_404(post_id)
    
    # Sử dụng lại hàm serialize_comment từ trên để đảm bảo dữ liệu đồng bộ
    def serialize_comment(c):
        # Lấy danh sách replies
        replies_data = []
        for reply in c.replies.filter_by(is_spam=False).order_by(Comment.created_at.asc()):
            replies_data.append(serialize_comment(reply))
        
        # Lấy thông tin author
        author_avatar = c.author.avatar or 'images/default-avatar.png'
        if not author_avatar.startswith('uploads/'):
            author_avatar = f'uploads/{author_avatar}' if not author_avatar.startswith('static/') else author_avatar.replace('static/', '')
        
        # Lấy thông tin media
        image = None
        video = None
        if c.image:
            image = f'uploads/{c.image}'
        elif c.video:
            video = f'uploads/{c.video}'
        
        return {
            'id': c.id,
            'content': c.content,
            'author': {
                'id': c.author.id,
                'name': c.author.name,
                'avatar': author_avatar
            },
            'image': image,
            'video': video,
            'sticker': c.sticker,
            'is_edited': c.is_edited,
            'created_at': c.created_at.strftime('%H:%M %d/%m/%Y'),
            'likes': c.likes_count,
            'is_liked': c.is_liked_by(current_user.id) if current_user.is_authenticated else False,
            'can_edit': c.can_edit(current_user) if current_user.is_authenticated else False,
            'can_delete': c.can_delete(current_user) if current_user.is_authenticated else False,
            'replies': replies_data
        }
    
    # Lấy tất cả bình luận không bị đánh dấu spam
    comments = Comment.query.filter_by(
        post_id=post_id, 
        parent_id=None,
        is_spam=False
    ).order_by(Comment.created_at.desc()).all()
    
    return jsonify({
        'comments': [serialize_comment(c) for c in comments],
        'total': len(comments)
    })

@app.route('/admin/post/<int:post_id>/delete', methods=['POST'])
@login_required
def admin_delete_post(post_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Không có quyền'}), 403
    
    post = Post.query.get_or_404(post_id)
    
    try:
        # 1. TRỪ ĐIỂM TÁC GIẢ (theo bảng của bạn: bị báo cáo đúng → -50 điểm)
        post.author.points = max(0, post.author.points - 50)
        update_user_badge(post.author)
        
        # 2. THÔNG BÁO CHO TÁC GIẢ
        notif = Notification(
            user_id=post.user_id,
            title="Bài viết của bạn đã bị xóa",
            message=f"Bài viết '{post.title[:50]}...' đã bị admin xóa do vi phạm báo cáo. Bạn bị trừ 50 điểm tích lũy.",
            type='post_deleted_penalty',
            related_id=post.id,
            related_user_id=current_user.id  # Admin nào xóa
        )
        db.session.add(notif)
        
        # 3. XÓA TẤT CẢ DỮ LIỆU LIÊN QUAN (đây là bước quan trọng để tránh lỗi)
        PostLike.query.filter_by(post_id=post_id).delete()          # Xóa like
        PostRating.query.filter_by(post_id=post_id).delete()        # Xóa rating
        HiddenPost.query.filter_by(post_id=post_id).delete()        # Xóa ẩn bài
        Report.query.filter_by(post_id=post_id).delete()            # Xóa báo cáo
        Comment.query.filter_by(post_id=post_id).delete()           # Xóa bình luận
        
        # 4. Xóa chính bài viết
        db.session.delete(post)
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Đã xóa bài viết, trừ 50 điểm tác giả và gửi thông báo!'})
    
    except Exception as e:
        db.session.rollback()
        print(f"Lỗi khi xóa bài viết {post_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

#Cảnh báo & Trừ điểm (không xóa bài)
@app.route('/admin/report/<int:report_id>/warn', methods=['POST'])
@login_required
def admin_warn_report(report_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Không có quyền!'}), 403
    
    report = Report.query.get_or_404(report_id)
    post = report.post
    
    try:
        # TRỪ 50 ĐIỂM TÁC GIẢ
        post.author.points = max(0, post.author.points - 50)
        update_user_badge(post.author)
        
        # THÔNG BÁO CẢNH BÁO CHO TÁC GIẢ
        notif = Notification(
            user_id=post.user_id,
            title="Cảnh báo: Bài viết của bạn vi phạm quy định",
            message=f"Bài viết '{post.title[:50]}...' đã nhận báo cáo hợp lệ. Bạn bị trừ 50 điểm. Vui lòng chỉnh sửa để tránh bị xóa.",
            type='post_warning_penalty',
            related_id=post.id,
            related_user_id=current_user.id
        )
        db.session.add(notif)
        
        # XÓA BÁO CÁO (đã xử lý xong)
        db.session.delete(report)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Đã cảnh báo và trừ điểm tác giả!'
        }, ensure_ascii=False)
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/admin/post/<int:post_id>/lock', methods=['POST'])
@app.route('/admin/post/<int:post_id>/unlock', methods=['POST'])
@login_required
def admin_toggle_post_lock(post_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Không có quyền'}), 403
    post = Post.query.get_or_404(post_id)
    action = request.path.split('/')[-1]
    post.is_locked = (action == 'lock')
    db.session.commit()
    return jsonify({'success': True})

@app.route('/admin/comment/<int:comment_id>/delete', methods=['POST'])
@login_required
def admin_delete_comment(comment_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Không có quyền'}), 403
    comment = Comment.query.get_or_404(comment_id)
    try:
        db.session.delete(comment)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

from sqlalchemy import func
from sqlalchemy.orm import joinedload

# Tìm và sửa lại hàm admin_dashboard trong app.py

@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Bạn không có quyền truy cập trang quản trị!', 'error')
        return redirect(url_for('home'))

    # --- 1. THỐNG KÊ TỔNG ---
    stats = {
        'total_users': User.query.count(),
        'total_posts': Post.query.count(),
        'total_experts': User.query.filter_by(is_verified_expert=True).count(),
        'total_points': db.session.query(func.sum(User.points)).scalar() or 0,
    }

    # --- 2. THỐNG KÊ THEO NGƯÒI DÙNG ---
    user_stats = db.session.query(
        User.id,
        User.name,
        User.email,
        User.role,
        User.is_verified_expert,
        User.points,
        User.avatar,
        User.is_active,
        func.count(Post.id).label('post_count'),
        func.coalesce(func.sum(Post.views), 0).label('total_views'),
        func.coalesce(func.sum(Post.likes), 0).label('total_likes'),
        func.coalesce(func.sum(Post.comments_count), 0).label('total_comments')
    ).outerjoin(Post, User.id == Post.user_id)\
     .group_by(User.id)\
     .order_by(func.count(Post.id).desc())\
     .limit(20).all()

    # --- 3. TÍNH TOẢN THEO CHU ĐỀ ---
    topic_stats = db.session.query(
        Post.category,
        func.count(Post.id).label('count')
    ).group_by(Post.category).all()

    topic_dict = {cat: count for cat, count in topic_stats}

    # --- 4. DỮ LIỆU DATA ---
    users = User.query.all()
    expert_requests = ExpertRequest.query.filter_by(status='pending').all()
    reports = Report.query.all()
    posts = Post.query.order_by(Post.created_at.desc()).limit(20).all()

    # --- 5. TÍNH TOÁN DỮ LIỆU DATA JSON CHO YÊU CẦU ---
    expert_requests_data = []
    for req in ExpertRequest.query.filter_by(status='pending').all():
        user = req.user
        total_posts = user.posts.count()
        total_comments = Comment.query.filter_by(user_id=user.id).count()
        
        avg_likes = 0
        if total_posts > 0:
            avg_result = db.session.query(func.avg(Post.likes))\
                                  .filter(Post.user_id == user.id)\
                                  .scalar()
            avg_likes = round(avg_result or 0, 1)
        
        expert_requests_data.append({
            'id': req.id,
            'user': {
                'id': user.id,
                'name': user.name,
                'email': user.email,
                'points': user.points,
                'avatar': user.avatar or 'images/default-avatar.png'
            },
            'category': req.category,
            'reason': req.reason,
            'certificate': req.certificate,
            'created_at': req.created_at.isoformat(),
            'status': req.status,
            'total_posts': total_posts,
            'total_comments': total_comments,
            'avg_likes': avg_likes
        })

    # --- 6. TÍNH TOÁN DỮ LIỆU DÀNH SÁCH CHUYÊN GIA + ẢNH BẰNG CẤP ---
    # Lấy danh sách các yêu cầu đã được duyệt để lấy ảnh bằng cấp
    approved_requests = ExpertRequest.query.filter_by(status='approved').all()
    expert_cert_map = {req.user_id: req.certificate for req in approved_requests}
    
    # Lấy danh sách chuyên gia (✅ QUAN TRỌNG ADMIN KHỎI KHÔNG HIỆN THỂ NÀY)
    verified_experts = User.query.filter(
        User.is_verified_expert == True,
        User.role != 'admin' # ✅ LOẠI BỎ ADMIN KHỎI KHÔI CÁI CHUYÊN GIA VÀO ADMIN
    ).all()

    # --- 7. RETURN TEMPLATE (DÙNG ADMIN RIÊNG) ---
    return render_template(
        'admin_dashboard.html',
        stats=stats,
        user_stats=user_stats,
        topic_stats=topic_dict,
        users=users,
        expert_requests=ExpertRequest.query.filter_by(status='pending').all(), # Giữ nguyên cho loop Jinja
        expert_requests_json=expert_requests_data,  # ← BIẾN JSON
        reports=reports,
        posts=posts,
        Comment=Comment,
        Post=Post, 
        verified_experts=verified_experts, # ← TRUYỀN DANH SÁCH CHUYÊN GIA (LOẠI BỎ ADMIN)
        expert_cert_map=expert_cert_map  # ← TRUYỀN ẢNH BẰNG CẤP
    )

# Hàm admin hủy tư cách chuyên gia 
@app.route('/admin/expert/<int:user_id>/revoke', methods=['POST'])
@login_required
def admin_revoke_expert(user_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Không có quyền!'}), 403
    
    user = User.query.get_or_404(user_id)
    
    if not user.is_verified_expert:
        flash('Người dùng này không phải là chuyên gia!', 'error')
        return redirect(url_for('admin_dashboard'))

    # Hủy tư cách chuyên gia
    user.is_verified_expert = False
    old_category = user.expert_category
    user.expert_category = None  # Xóa lĩnh vực
    
    # Gửi thông báo cho user bị hủy
    reason = request.form.get('reason', 'Vi phạm quy định nền tảng')
    notif = Notification(
        user_id=user.id,
        title="⚠️ Tư cách Chuyên gia đã bị thu hồi",
        message=f"Admin đã thu hồi tư cách chuyên gia của bạn (Lĩnh vực: {old_category}). Lý do: {reason}",
        type='expert_revoked',
        related_user_id=current_user.id
    )
    db.session.add(notif)
    db.session.commit()
    
    flash(f'Đã hủy tư cách chuyên gia của {user.name}!', 'info')
    return redirect(url_for('admin_dashboard'))


@app.route('/api/admin/notifications')
@login_required
def api_admin_notifications():
    if current_user.role != 'admin':
        return jsonify([])

    notifs = Notification.query.filter_by(user_id=current_user.id)\
                               .order_by(Notification.is_read.asc(), Notification.created_at.desc())\
                               .limit(30).all()

    results = []
    for n in notifs:
        icon = '🔔'
        if n.type == 'report_post': icon = '🚩'
        elif n.type == 'report_comment': icon = '💬'
        elif n.type == 'expert_request': icon = '👨‍⚕️'
        elif n.type == 'new_user': icon = '👶'
        elif n.type == 'expert_action': icon = '✅'

        # CHUYỂN RELATED_USER THÀNH DICT AN TOÀN
        related_user_data = None
        if n.related_user:
            related_user_data = {
                'id': n.related_user.id,
                'name': n.related_user.name,
                'email': n.related_user.email,
                'avatar': n.related_user.avatar or 'images/default-avatar.png',
                # Nếu related_user là ExpertRequest thì thêm trường đặc biệt (tùy chọn)
                'is_expert_request': isinstance(n.related_user, ExpertRequest)
            }

        results.append({
            'id': n.id,
            'title': f"{icon} {n.title}",
            'message': n.message,
            'type': n.type,
            'is_read': n.is_read,
            'created_at': n.created_at.strftime('%H:%M %d/%m'),
            'related_user': related_user_data,
            'action_link': (
                '/admin#experts' if n.type in ['expert_request', 'expert_action'] else
                '/admin#reports' if n.type in ['report_post', 'report_comment'] else
                '/admin#users'
            )
        })

    return jsonify(results)

# ADMIN chọn bài vieetx hữu ích
@app.route('/admin/post/<int:post_id>/mark_helpful', methods=['POST'])
@login_required
def mark_post_helpful(post_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Không có quyền!'}), 403
    
    post = Post.query.get_or_404(post_id)
    
    # Kiểm tra đã đánh dấu chưa
    if post.is_helpful:
        return jsonify({'error': 'Bài viết đã được đánh dấu hữu ích rồi!'}), 400
    
    post.is_helpful = True
    post.author.points += 50  # CỘNG 50 ĐIỂM
    update_user_badge(post.author)
    
    # Thông báo cho tác giả
    notif = Notification(
        user_id=post.user_id,
        title="🎉 Bài viết của bạn được đánh giá hữu ích!",
        message=f"Admin đã chọn bài '{post.title[:50]}...' là bài viết hữu ích. Bạn nhận được +50 điểm!",
        type='admin_award',
        related_id=post.id,
        related_user_id=current_user.id
    )
    db.session.add(notif)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Đã đánh dấu bài viết hữu ích!'})

# Admin  TRỪ ĐIỂM KHI BỊ BÁO CÁO ĐÚNG (-50 ĐIỂM)
@app.route('/admin/report/<int:report_id>/confirm', methods=['POST'])
@login_required
def confirm_report(report_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Không có quyền!'}), 403
    
    report = Report.query.get_or_404(report_id)
    post = report.post
    
    # === TRỪ 50 ĐIỂM CHO TÁC GIẢ BÀI BỊ BÁO CÁO ĐÚNG ===
    post.author.points = max(0, post.author.points - 50)
    update_user_badge(post.author)
    
    # Xóa bài viết
    db.session.delete(post)
    
    # Thông báo cho tác giả
    notif = Notification(
        user_id=post.user_id,
        title="⚠️ Bài viết của bạn vi phạm quy định",
        message=f"Bài viết '{post.title[:50]}...' đã bị xóa do vi phạm. Bạn bị trừ 50 điểm.",
        type='warning',
        related_user_id=current_user.id
    )
    db.session.add(notif)
    
    # Xóa báo cáo
    db.session.delete(report)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Đã xử lý báo cáo và trừ điểm!'})


# XÓA BÀI VIẾT (CHỦ BÀI)
@app.route('/post/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_post_by_owner(post_id):
    post = Post.query.get_or_404(post_id)
    
    # Chỉ cho phép chủ bài hoặc admin xóa
    if post.user_id != current_user.id and current_user.role != 'admin':
        return jsonify({'error': 'Không có quyền xóa bài này!'}), 403
    
    try:
        # Xóa tất cả dữ liệu liên quan
        PostLike.query.filter_by(post_id=post_id).delete()
        PostRating.query.filter_by(post_id=post_id).delete()
        HiddenPost.query.filter_by(post_id=post_id).delete()
        Comment.query.filter_by(post_id=post_id).delete()
        Report.query.filter_by(post_id=post_id).delete()
        
        db.session.delete(post)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Đã xóa bài viết thành công!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ẨN BÀI VIẾT
@app.route('/post/<int:post_id>/hide', methods=['POST'])
@login_required
def hide_post(post_id):
    post = Post.query.get_or_404(post_id)
    
    # Kiểm tra đã ẩn chưa
    existing = HiddenPost.query.filter_by(
        user_id=current_user.id,
        post_id=post_id
    ).first()
    
    if existing:
        return jsonify({'error': 'Bài viết đã được ẩn rồi!'}), 400
    
    hidden = HiddenPost(user_id=current_user.id, post_id=post_id)
    db.session.add(hidden)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Đã ẩn bài viết khỏi bảng tin!'})

# BỎ ẨN BÀI VIẾT
@app.route('/post/<int:post_id>/unhide', methods=['POST'])
@login_required
def unhide_post(post_id):
    hidden = HiddenPost.query.filter_by(
        user_id=current_user.id,
        post_id=post_id
    ).first()
    
    if not hidden:
        return jsonify({'error': 'Bài viết chưa được ẩn!'}), 400
    
    db.session.delete(hidden)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Đã hiện lại bài viết!'})

# === GỬI LỜI MỜI KẾT BẠN ===
@app.route('/send_friend_request/<int:user_id>', methods=['POST'])
@login_required
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
@app.route('/accept_friend_request/<int:request_id>', methods=['POST'])
@login_required
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
@app.route('/reject_friend_request/<int:request_id>', methods=['POST'])
@login_required
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
@app.route('/cancel_friend_request/<int:user_id>', methods=['POST'])
@login_required
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
@app.route('/unfriend/<int:user_id>', methods=['POST'])
@login_required
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
@app.route('/friendship_status/<int:user_id>')
@login_required
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
@app.route('/friends')
@login_required
def friends():
    # Sử dụng cùng hàm với trang home
    friends_list = get_friends(current_user)
    pending_requests = get_pending_requests(current_user)
    sent_requests = get_sent_requests(current_user)
    suggested_users = get_suggested_users(current_user, limit=10)

    return render_template(
        'friends.html',
        friends=friends_list,
        pending_requests=pending_requests,
        sent_requests=sent_requests,
        suggested_users=suggested_users
    )

# === CHAT ROUTE ===
@app.route('/chat/<int:user_id>')
@login_required
def chat(user_id):
    # ✅ KIỂM TRA BẠN BÈ ĐÚNG CÁCH
    friendship = Friendship.query.filter(
        ((Friendship.user1_id == current_user.id) & (Friendship.user2_id == user_id)) |
        ((Friendship.user1_id == user_id) & (Friendship.user2_id == current_user.id))
    ).first()
    
    if not friendship:
        return render_template('not_friend.html', other_id=user_id)
    
    other_user = User.query.get_or_404(user_id)
    return render_template('chat.html', other_user=other_user)

@socketio.on('join_chat')
def on_join_chat(data):
    user_id = data['user_id']
    friend_id = data['friend_id']
    room = f"chat_{min(user_id, friend_id)}_{max(user_id, friend_id)}"
    join_room(room)
    print(f"User {user_id} joined room {room}")  # DEBUG

@socketio.on('send_message')
def handle_message(data):
    sender_id = data['sender_id']
    receiver_id = data['receiver_id']
    content = data['content'].strip()
    
    if not content or sender_id == receiver_id:
        return

    # Lưu vào DB
    msg = Message(sender_id=sender_id, receiver_id=receiver_id, content=content)
    db.session.add(msg)
    db.session.commit()

    timestamp = vietnam_now().strftime('%H:%M %d/%m')
    sender = User.query.get(sender_id)

    message_data = {
        'sender_id': sender_id,
        'sender_name': sender.name,
        'content': content,
        'timestamp': timestamp
    }

    room = f"chat_{min(sender_id, receiver_id)}_{max(sender_id, receiver_id)}"
    emit('receive_message', message_data, room=room, include_self=True, broadcast=True)
    print(f"✅ Sent to room {room}: {content}")

# THÊM VÀO app.py - THAY THẾ PHẦN VIDEO CALL SOCKET EVENTS

# Dictionary lưu socket_id của users đang online
online_users = {}

@socketio.on('connect')
def handle_connect():
    print(f'✅ User connected: {request.sid}')

@socketio.on('disconnect')
def handle_disconnect():
    # Xóa user khỏi danh sách online
    for user_id, sid in list(online_users.items()):
        if sid == request.sid:
            del online_users[user_id]
            print(f'❌ User {user_id} disconnected')
    print(f'Client disconnected: {request.sid}')

@socketio.on('register_user')
def handle_register_user(data):
    """Đăng ký user_id với socket_id"""
    user_id = data.get('user_id')
    if user_id:
        online_users[user_id] = request.sid
        print(f'📝 Registered user {user_id} with socket {request.sid}')
        print(f'Online users: {online_users}')

@socketio.on('video_call_request')
def handle_video_call_request(data):
    """Xử lý yêu cầu gọi video"""
    from_user = data.get('from')
    to_user = data.get('to')
    caller_name = data.get('caller_name')
    
    print(f'📞 Video call request: {from_user} -> {to_user}')
    print(f'Online users: {online_users}')
    
    # Lấy socket_id của người nhận
    to_socket = online_users.get(to_user)
    
    if to_socket:
        print(f'✅ Sending call notification to socket {to_socket}')
        # Gửi thông báo đến người nhận cụ thể
        emit('video_call_request', {
            'from': from_user,
            'caller_name': caller_name
        }, room=to_socket)
    else:
        print(f'❌ User {to_user} is not online')
        # Thông báo cho người gọi rằng đối phương offline
        emit('call_failed', {
            'message': 'Người dùng không trực tuyến'
        }, room=request.sid)

@socketio.on('video_call_accepted')
def handle_call_accepted(data):
    """Xử lý khi chấp nhận cuộc gọi"""
    from_user = data.get('from')
    to_user = data.get('to')
    
    print(f'✅ Call accepted: {from_user} -> {to_user}')
    
    to_socket = online_users.get(to_user)
    if to_socket:
        emit('video_call_accepted', {
            'from': from_user
        }, room=to_socket)

@socketio.on('video_call_rejected')
def handle_call_rejected(data):
    """Xử lý khi từ chối cuộc gọi"""
    from_user = data.get('from')
    to_user = data.get('to')
    
    print(f'❌ Call rejected: {from_user} -> {to_user}')
    
    to_socket = online_users.get(to_user)
    if to_socket:
        emit('video_call_rejected', {
            'from': from_user
        }, room=to_socket)

@socketio.on('video_call_offer')
def handle_offer(data):
    """Chuyển tiếp WebRTC offer"""
    to_user = data.get('to')
    offer = data.get('offer')
    from_user = current_user.id if current_user.is_authenticated else None
    
    print(f'📤 Sending offer: {from_user} -> {to_user}')
    
    to_socket = online_users.get(to_user)
    if to_socket:
        emit('video_call_offer', {
            'from': from_user,
            'offer': offer
        }, room=to_socket)

@socketio.on('video_call_answer')
def handle_answer(data):
    """Chuyển tiếp WebRTC answer"""
    to_user = data.get('to')
    answer = data.get('answer')
    from_user = current_user.id if current_user.is_authenticated else None
    
    print(f'📤 Sending answer: {from_user} -> {to_user}')
    
    to_socket = online_users.get(to_user)
    if to_socket:
        emit('video_call_answer', {
            'from': from_user,
            'answer': answer
        }, room=to_socket)

@socketio.on('ice_candidate')
def handle_ice_candidate(data):
    """Chuyển tiếp ICE candidate"""
    to_user = data.get('to')
    candidate = data.get('candidate')
    from_user = current_user.id if current_user.is_authenticated else None
    
    to_socket = online_users.get(to_user)
    if to_socket:
        emit('ice_candidate', {
            'from': from_user,
            'candidate': candidate
        }, room=to_socket)

@socketio.on('call_ended')
def handle_call_ended(data):
    """Xử lý khi kết thúc cuộc gọi"""
    to_user = data.get('to')
    from_user = current_user.id if current_user.is_authenticated else None
    
    print(f'📴 Call ended: {from_user} -> {to_user}')
    
    to_socket = online_users.get(to_user)
    if to_socket:
        emit('call_ended', {
            'from': from_user
        }, room=to_socket)

# ============================================
# CẬP NHẬT CHAT HISTORY API
# ============================================

@app.route('/chat/history/<int:friend_id>')
def chat_history(friend_id):
    from flask_login import current_user
    
    if not current_user.is_authenticated:
        return jsonify([])
    
    messages = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.receiver_id == friend_id)) |
        ((Message.sender_id == friend_id) & (Message.receiver_id == current_user.id))
    ).order_by(Message.timestamp.asc()).all()

    return jsonify([{
        'sender_id': m.sender_id,
        'sender_name': m.sender.name,
        'content': m.content,
        'timestamp': m.timestamp.strftime('%H:%M %d/%m'),
        'type': getattr(m, 'type', 'text')  # Thêm type
    } for m in messages])

# SỬA LẠI ROUTE ĐÁNH GIÁ SAO
@app.route('/rate/<int:post_id>', methods=['POST'])
@login_required
def rate_post(post_id):
    post = Post.query.get_or_404(post_id)
    data = request.get_json()
    stars = data.get('stars', 0)
    
    if stars < 1 or stars > 5:
        return jsonify({'error': 'Số sao phải từ 1-5'}), 400
    
    # Kiểm tra đã đánh giá chưa
    existing_rating = PostRating.query.filter_by(
        user_id=current_user.id,
        post_id=post_id
    ).first()
    
    if existing_rating:
        # Cập nhật đánh giá
        old_stars = existing_rating.stars
        existing_rating.stars = stars
        existing_rating.created_at = vietnam_now()
        
        # Cập nhật rating trung bình
        total = post.rating * post.rating_count
        total = total - old_stars + stars
        post.rating = total / post.rating_count
    else:
        # Thêm đánh giá mới
        new_rating = PostRating(
            user_id=current_user.id,
            post_id=post_id,
            stars=stars
        )
        db.session.add(new_rating)
        
        # Cập nhật rating trung bình
        if not hasattr(post, 'rating') or post.rating is None:
            post.rating = 0
            post.rating_count = 0
        
        total = post.rating * post.rating_count + stars
        post.rating_count += 1
        post.rating = total / post.rating_count
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'rating': round(post.rating, 1),
        'rating_count': post.rating_count,
        'user_rating': stars
    })

@app.route('/user/<int:user_id>')
def user_profile(user_id):
    viewed_user = User.query.get_or_404(user_id)
    
    # Lấy bài viết của người này
    posts = Post.query.filter_by(user_id=user_id).order_by(Post.created_at.desc()).limit(20).all()
    
    # Kiểm tra trạng thái kết bạn (nếu đang đăng nhập)
    friendship_status = 'not_authenticated'
    if current_user.is_authenticated:
        friendship_status = current_user.get_friendship_status(user_id)
    
    # Kiểm tra xem có phải chính mình không
    is_own_profile = current_user.is_authenticated and current_user.id == user_id

    return render_template(
        'user_profile.html',
        user=viewed_user,
        posts=posts,
        friendship_status=friendship_status,
        is_own_profile=is_own_profile,
        db=db,
        Post=Post,
        func=func
    )
                
# LẤY ĐÁNH GIÁ CỦA USER
@app.route('/api/post/<int:post_id>/my-rating')
@login_required
def get_my_rating(post_id):
    rating = PostRating.query.filter_by(
        user_id=current_user.id,
        post_id=post_id
    ).first()
    
    if rating:
        return jsonify({'stars': rating.stars})
    return jsonify({'stars': 0})

#để theo dõi lượt xem trên trang home
@app.route('/track_home_view/<int:post_id>', methods=['POST'])
def track_home_view(post_id):
    post = Post.query.get_or_404(post_id)
    
    # Kiểm tra xem người dùng đã xem bài viết này trong phiên hiện tại chưa
    if current_user.is_authenticated:
        # Lấy danh sách các bài viết đã xem trên trang home trong phiên của người dùng
        home_viewed_posts = session.get('home_viewed_posts', [])
        
        # Chỉ tăng lượt xem nếu chưa xem bài viết này trên trang home trong phiên hiện tại
        if post_id not in home_viewed_posts:
            post.views += 1
            db.session.commit()
            
            # Thêm bài viết vào danh sách đã xem trên trang home
            home_viewed_posts.append(post_id)
            session['home_viewed_posts'] = home_viewed_posts
    else:
        # Đối với người dùng chưa đăng nhập, sử dụng cookie để theo dõi
        home_viewed_posts = request.cookies.get('home_viewed_posts', '').split(',')
        home_viewed_posts = [int(p) for p in home_viewed_posts if p.isdigit()]
        
        if post_id not in home_viewed_posts:
            post.views += 1
            db.session.commit()
            
            # Thêm bài viết vào cookie
            home_viewed_posts.append(post_id)
            response = make_response(jsonify({'success': True, 'views': post.views}))
            response.set_cookie('home_viewed_posts', ','.join(map(str, home_viewed_posts)), max_age=3600) # 1 giờ
            return response
    
    return jsonify({'success': True, 'views': post.views})

#khi nào người dùng nhấp vào bài viết 
@app.route('/track_view/<int:post_id>', methods=['POST'])
@login_required
def track_view(post_id):
    post = Post.query.get_or_404(post_id)
    post.views += 1
    db.session.commit()
    return jsonify({'success': True, 'views': post.views})

# xem chi tiết thống kê của một người dùng
@app.route('/admin/user/<int:user_id>/stats')
@login_required
def admin_user_stats(user_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Không có quyền!'}), 403
    
    user = User.query.get_or_404(user_id)
    
    # Lấy thống kê chi tiết của người dùng
    posts = Post.query.filter_by(user_id=user_id).all()
    
    # Tính toán thống kê
    total_views = sum(post.views for post in posts)
    total_likes = sum(post.likes for post in posts)
    total_comments = sum(post.comments_count for post in posts)
    
    # Lấy thống kê theo từng bài viết
    post_stats = []
    for post in posts:
        post_stats.append({
            'id': post.id,
            'title': post.title,
            'views': post.views,
            'likes': post.likes,
            'comments': post.comments_count,
            'created_at': post.created_at.strftime('%d/%m/%Y')
        })
    
    return jsonify({
        'user': {
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'role': user.role,
            'is_verified_expert': user.is_verified_expert,
            'points': user.points
        },
        'stats': {
            'total_posts': len(posts),
            'total_views': total_views,
            'total_likes': total_likes,
            'total_comments': total_comments
        },
        'post_stats': post_stats
    })


# ====================================
# EXPERT DASHBOARD
# ====================================
@app.route('/expert/dashboard')
@expert_required
def expert_dashboard():
    # ✅ LẤY TẤT CẢ BÀI VIẾT CỦA CHUYÊN GIA (DÙNG Post MODEL THÔNG THƯỜNG)
    expert_posts = Post.query.filter_by(
        user_id=current_user.id,
        is_expert_post=True  # ← Chỉ lấy bài đánh dấu là chuyên gia
    ).all()
    
    # Lấy ID của tất cả bài viết
    post_ids = [post.id for post in expert_posts]
    
    # ✅ THỐNG KÊ ĐÚNG
    stats = {
        'total_views': sum(post.views for post in expert_posts),
        'followers_count': current_user.followers.count(),
        'posts_count': len(expert_posts),
        'consultations_count': Booking.query.join(TimeSlot).filter(
            TimeSlot.expert_id == current_user.id
        ).count(),
        'new_comments': Comment.query.filter(
            Comment.post_id.in_(post_ids) if post_ids else False
        ).count(),
        'new_likes': sum(post.likes for post in expert_posts),
        'new_followers': current_user.followers.count(),
        'new_consultations': Booking.query.join(TimeSlot).filter(
            TimeSlot.expert_id == current_user.id,
            Booking.status == 'scheduled'
        ).count()
    }
    
    # ✅ BÀI VIẾT GẦN ĐÂY (5 BÀI)
    recent_posts = Post.query.filter_by(
        user_id=current_user.id,
        is_expert_post=True
    ).order_by(Post.created_at.desc()).limit(5).all()
    
    # ✅ LỊCH TƯ VẤN SẮP TỚI
    now = vietnam_now()
    upcoming_consultations = Booking.query.join(TimeSlot).filter(
        TimeSlot.expert_id == current_user.id,
        TimeSlot.start_time >= now,
        Booking.status == 'scheduled'
    ).order_by(TimeSlot.start_time).limit(5).all()
    
    # ✅ CÂU HỎI CHƯA TRẢ LỜI (LẤY TỪ COMMENTS CHƯA CÓ REPLY)
    unanswered_questions = Comment.query.filter(
        Comment.post_id.in_(post_ids) if post_ids else False,
        ~Comment.id.in_(
            db.session.query(Comment.parent_id).filter(Comment.parent_id.isnot(None))
        )
    ).order_by(Comment.created_at.desc()).limit(5).all()
    
    return render_template(
        'expert/dashboard.html',
        stats=stats,
        recent_posts=recent_posts,
        upcoming_consultations=upcoming_consultations,
        unanswered_questions=unanswered_questions
    )


# ====================================
# EXPERT POSTS - QUẢN LÝ BÀI VIẾT CHUYÊN GIA
# ====================================
@app.route('/expert/posts', methods=['GET', 'POST'])
@expert_required
def expert_posts():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        category = request.form.get('category', 'other')
        
        if not title or not content:
            flash('Vui lòng điền đầy đủ thông tin!', 'error')
            return redirect(url_for('expert_posts'))
        
        # Xử lý upload media
        images_list = []
        video_file = None
        if 'media' in request.files:
            files = request.files.getlist('media')
            for file in files:
                if file and file.filename:
                    filename = secure_filename(f"{int(time.time())}_{file.filename}")
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(filepath)
                    
                    if file.mimetype.startswith('video/'):
                        video_file = filename
                    else:
                        images_list.append(filename)
        
        # ✅ TẠO BÀI VIẾT THƯỜNG NHƯNG ĐÁNH DẤU LÀ CỦA CHUYÊN GIA
        post = Post(
            user_id=current_user.id,
            title=title,
            content=content,
            category=category,
            images=','.join(images_list) if images_list else None,
            video=video_file,
            is_expert_post=True,  # ← Đánh dấu là bài chuyên gia
            post_type='expert_advice'  # ← Loại bài tư vấn
        )
        
        db.session.add(post)
        db.session.commit()
        
        # Thông báo cho followers
        followers = Follow.query.filter_by(followed_id=current_user.id).all()
        for follower in followers:
            notif = Notification(
                user_id=follower.follower_id,
                title="Bài viết tư vấn mới từ chuyên gia",
                message=f"{current_user.name} vừa đăng bài: {title[:50]}...",
                type='expert_post',
                related_id=post.id,
                related_user_id=current_user.id
            )
            db.session.add(notif)
        
        db.session.commit()
        flash('Bài viết tư vấn đã được tạo thành công!', 'success')
        return redirect(url_for('expert_posts'))
    
    # ✅ GET - LẤY TẤT CẢ BÀI VIẾT CỦA CHUYÊN GIA
    posts = Post.query.filter_by(
        user_id=current_user.id,
        is_expert_post=True
    ).order_by(Post.created_at.desc()).all()
    
    return render_template('expert/posts.html', posts=posts)



# ✅ 1. TRANG QUẢN LÝ KHUNG GIỜ
@app.route('/expert/schedule', methods=['GET', 'POST'])
@expert_required
def expert_schedule():
    if request.method == 'POST':
        action = request.form.get('action', 'create')
        
        if action == 'delete':
            slot_id = request.form.get('slot_id')
            slot = TimeSlot.query.get_or_404(slot_id)
            
            if slot.expert_id != current_user.id:
                flash('Không có quyền xóa khung giờ này!', 'error')
                return redirect(url_for('expert_schedule'))
            
            # Nếu có booking → thông báo cho người đặt
            if slot.booking:
                notif = Notification(
                    user_id=slot.booking.user_id,
                    title="Khung giờ tư vấn bị hủy",
                    message=f"Chuyên gia {current_user.name} đã hủy khung giờ lúc {slot.start_time.strftime('%H:%M %d/%m/%Y')}",
                    type='booking_cancelled'
                )
                db.session.add(notif)
            
            db.session.delete(slot)
            db.session.commit()
            flash('Đã xóa khung giờ thành công!', 'success')
            return redirect(url_for('expert_schedule'))
        
        # CREATE / UPDATE slot
        slot_id = request.form.get('slot_id')
        date_str = request.form.get('date')
        start_time_str = request.form.get('start_time')
        duration_str = request.form.get('duration', '30')
        max_participants_str = request.form.get('max_participants', '1')
        notes = request.form.get('notes', '')
        
        try:
            # Parse ngày + giờ
            start_datetime_naive = datetime.strptime(f"{date_str} {start_time_str}", '%Y-%m-%d %H:%M')
            # Chuyển sang giờ Việt Nam
            vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
            start_datetime = vn_tz.localize(start_datetime_naive)
            duration = int(duration_str)
            end_datetime = start_datetime + timedelta(minutes=duration)
            
            max_participants = int(max_participants_str)
            if max_participants < 1:
                max_participants = 1
                
        except ValueError as e:
            flash(f'Dữ liệu ngày/giờ không hợp lệ: {str(e)}', 'error')
            return redirect(url_for('expert_schedule'))
        except Exception as e:
            flash(f'Có lỗi xảy ra khi xử lý: {str(e)}', 'error')
            return redirect(url_for('expert_schedule'))
        
        if slot_id:  # EDIT
            slot = TimeSlot.query.get_or_404(slot_id)
            if slot.expert_id != current_user.id:
                flash('Không có quyền chỉnh sửa khung giờ này!', 'error')
                return redirect(url_for('expert_schedule'))
            
            slot.start_time = start_datetime
            slot.end_time = end_datetime
            slot.max_participants = max_participants
            slot.notes = notes
            flash('Đã cập nhật khung giờ thành công!', 'success')
        
        else:  # CREATE
            slot = TimeSlot(
                expert_id=current_user.id,
                start_time=start_datetime,
                end_time=end_datetime,
                max_participants=max_participants,
                notes=notes,
                status='available'
            )
            db.session.add(slot)
            flash('Đã tạo khung giờ mới thành công!', 'success')
        
        db.session.commit()
        return redirect(url_for('expert_schedule'))

    # GET - Hiển thị danh sách
    now = vietnam_now()
    min_date = now.strftime('%Y-%m-%d')  # ← Chuẩn bị giá trị min cho input date

    # Lấy tất cả khung giờ của chuyên gia (không filter >= now để thấy cả lịch cũ)
    time_slots = TimeSlot.query.filter_by(expert_id=current_user.id)\
                             .order_by(TimeSlot.start_time).all()

    return render_template(
        'expert/schedule.html',
        time_slots=time_slots,
        min_date=min_date  # ← Truyền biến này để template dùng min="{{ min_date }}"
    )

# ✅ 2. HỦY KHUNG GIỜ
@app.route('/expert/time-slot/<int:slot_id>/cancel', methods=['POST'])
@expert_required
def cancel_time_slot(slot_id):
    slot = TimeSlot.query.get_or_404(slot_id)
    
    if slot.expert_id != current_user.id:
        return jsonify({'error': 'Không có quyền!'}), 403
    
    if slot.booking:
        # Thông báo cho người đã đặt
        notif = Notification(
            user_id=slot.booking.user_id,
            title="Khung giờ tư vấn bị hủy",
            message=f"Chuyên gia {current_user.name} đã hủy khung giờ lúc {slot.start_time.strftime('%H:%M %d/%m/%Y')}",
            type='booking_cancelled'
        )
        db.session.add(notif)
        
        # Xóa booking
        db.session.delete(slot.booking)
    
    slot.status = 'cancelled'
    db.session.commit()
    
    return jsonify({'success': True})

# ✅ 3. XEM KHUNG GIỜ CỦA CHUYÊN GIA (Người dùng)
@app.route('/expert/<int:expert_id>/slots')
@login_required
def view_expert_slots(expert_id):
    expert = User.query.get_or_404(expert_id)
    
    if not expert.is_verified_expert:
        flash('Người này không phải chuyên gia!', 'error')
        return redirect(url_for('home'))
    
    # Lấy khung giờ còn trống
    now = vietnam_now()
    available_slots = TimeSlot.query.filter_by(
        expert_id=expert_id,
        status='available'
    ).filter(TimeSlot.start_time >= now).order_by(TimeSlot.start_time).all()
    
    return render_template('expert_slots.html', expert=expert, slots=available_slots)

# ✅ 4. ĐẶT LỊCH TƯ VẤN
@app.route('/book-slot/<int:slot_id>', methods=['POST'])
@login_required
def book_slot(slot_id):
    slot = TimeSlot.query.get_or_404(slot_id)
    
    # Kiểm tra khung giờ
    if slot.status != 'available':
        return jsonify({'error': 'Khung giờ không còn trống!'}), 400
    
    if slot.start_time <= vietnam_now():
        return jsonify({'error': 'Khung giờ đã qua!'}), 400
    
    # Kiểm tra đã đặt chưa
    existing = Booking.query.filter_by(user_id=current_user.id, time_slot_id=slot_id).first()
    if existing:
        return jsonify({'error': 'Bạn đã đặt khung giờ này rồi!'}), 400
    
    # Tạo booking
    booking = Booking(
        user_id=current_user.id,
        time_slot_id=slot_id,
        notes=request.form.get('notes', ''),
        status='scheduled'
    )
    db.session.add(booking)
    
    # Cập nhật trạng thái slot
    slot.status = 'booked'
    
    # Thông báo cho chuyên gia
    notif = Notification(
        user_id=slot.expert_id,
        title="Có lịch tư vấn mới",
        message=f"{current_user.name} đã đặt lịch tư vấn lúc {slot.start_time.strftime('%H:%M %d/%m/%Y')}",
        type='new_booking',
        related_user_id=current_user.id
    )
    db.session.add(notif)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Đặt lịch thành công!'
    })

# ✅ 5. HỦY LỊCH ĐÃ ĐẶT (Người dùng)
@app.route('/cancel-booking/<int:booking_id>', methods=['POST'])
@login_required
def cancel_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    
    if booking.user_id != current_user.id:
        return jsonify({'error': 'Không có quyền!'}), 403
    
    # Giải phóng khung giờ
    slot = booking.time_slot
    slot.status = 'available'
    
    # Thông báo cho chuyên gia
    notif = Notification(
        user_id=slot.expert_id,
        title="Lịch tư vấn bị hủy",
        message=f"{current_user.name} đã hủy lịch tư vấn lúc {slot.start_time.strftime('%H:%M %d/%m/%Y')}",
        type='booking_cancelled',
        related_user_id=current_user.id
    )
    db.session.add(notif)
    
    db.session.delete(booking)
    db.session.commit()
    
    return jsonify({'success': True})

# ✅ 6. XEM LỊCH ĐÃ ĐẶT (Người dùng)
@app.route('/my-bookings')
@login_required
def my_bookings():
    now = vietnam_now()
    
    upcoming = Booking.query.filter_by(user_id=current_user.id, status='scheduled')\
                           .join(TimeSlot)\
                           .filter(TimeSlot.start_time >= now)\
                           .order_by(TimeSlot.start_time).all()
    
    past = Booking.query.filter_by(user_id=current_user.id)\
                       .join(TimeSlot)\
                       .filter(TimeSlot.start_time < now)\
                       .order_by(TimeSlot.start_time.desc()).all()
    
    return render_template('my_bookings.html', upcoming=upcoming, past=past)


# ====================================
# EXPERT ANALYTICS - THỐNG KÊ
# ====================================
@app.route('/expert/analytics')
@expert_required
def expert_analytics():
    # ✅ LẤY TẤT CẢ BÀI VIẾT CỦA CHUYÊN GIA
    expert_posts = Post.query.filter_by(
        user_id=current_user.id,
        is_expert_post=True
    ).all()
    
    # ✅ TÍNH TOÁN THỐNG KÊ
    total_views = sum(post.views for post in expert_posts)
    total_likes = sum(post.likes for post in expert_posts)
    total_comments = sum(post.comments_count for post in expert_posts)
    
    stats = {
        'total_views': total_views,
        'total_likes': total_likes,
        'total_comments': total_comments,
        'followers_count': current_user.followers.count(),
        'posts_count': len(expert_posts)
    }
    
    # ✅ THỐNG KÊ THEO DANH MỤC
    category_stats = {}
    for post in expert_posts:
        cat = post.category or 'other'
        if cat not in category_stats:
            category_stats[cat] = {'count': 0, 'views': 0}
        category_stats[cat]['count'] += 1
        category_stats[cat]['views'] += post.views
    
    # ✅ TOP BÀI VIẾT
    top_posts = sorted(expert_posts, key=lambda x: x.views, reverse=True)[:5]
    
    return render_template(
        'expert/analytics.html',
        stats=stats,
        category_stats=category_stats,
        top_posts=top_posts
    )

# ====================================
# EXPERT PROFILE - HỒ SƠ CHUYÊN GIA
# ====================================
@app.route('/expert/profile', methods=['GET', 'POST'])
@expert_required
def expert_profile():
    if request.method == 'POST':
        try:
            # Cập nhật thông tin cơ bản
            current_user.name = request.form.get('name', '').strip()
            current_user.bio = request.form.get('bio', '').strip()
            
            # Cập nhật thông tin chuyên môn
            current_user.specialty = request.form.get('specialty', '').strip()
            current_user.experience_years = int(request.form.get('experience_years', 0))
            current_user.workplace = request.form.get('workplace', '').strip()
            current_user.license_number = request.form.get('license_number', '').strip()
            
            # Ngày hết hạn chứng chỉ
            license_expiry_str = request.form.get('license_expiry', '')
            if license_expiry_str:
                from datetime import datetime
                current_user.license_expiry = datetime.strptime(license_expiry_str, '%Y-%m-%d')
            
            # Phí tư vấn
            current_user.consultation_fee = float(request.form.get('consultation_fee', 0))
            
            # Học vấn và chứng chỉ
            current_user.education = request.form.get('education', '').strip()
            current_user.certifications = request.form.get('certifications', '').strip()
            
            # Trạng thái hoạt động
            current_user.availability = request.form.get('availability', 'available')
            
            # Xử lý upload avatar
            if 'avatarInput' in request.files:
                file = request.files['avatarInput']
                if file and file.filename:
                    filename = secure_filename(f"expert_{current_user.id}_{int(time.time())}_{file.filename}")
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(filepath)
                    current_user.avatar = filename  # ← KHÔNG CẦN 'uploads/' Ở ĐÂY
            
            db.session.commit()
            flash('Hồ sơ đã được cập nhật thành công!', 'success')
            return redirect(url_for('expert_profile'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Có lỗi xảy ra: {str(e)}', 'error')
            return redirect(url_for('expert_profile'))
    
    # GET - Hiển thị form
    return render_template('expert/profile.html')

# ====================================
# XÓA BÀI VIẾT CHUYÊN GIA
# ====================================
@app.route('/expert/post/<int:post_id>/delete', methods=['POST'])
@expert_required
def expert_delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    
    if post.user_id != current_user.id:
        return jsonify({'error': 'Không có quyền xóa bài viết này!'}), 403
    
    try:
        # Xóa dữ liệu liên quan
        PostLike.query.filter_by(post_id=post_id).delete()
        PostRating.query.filter_by(post_id=post_id).delete()
        HiddenPost.query.filter_by(post_id=post_id).delete()
        Comment.query.filter_by(post_id=post_id).delete()
        Report.query.filter_by(post_id=post_id).delete()
        
        db.session.delete(post)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Đã xóa bài viết!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ====================================
# XEM CHI TIẾT BÀI VIẾT CHUYÊN GIA
# ====================================
@app.route('/expert/post/<int:post_id>')
def expert_post_detail(post_id):
    post = Post.query.get_or_404(post_id)
    
    # Tăng view count
    post.views += 1
    db.session.commit()
    
    return render_template('post_detail.html', post=post)

# ====================================
# QUÊN MẬT KHẨU - BƯỚC 1: NHẬP SỐ ĐIỆN THOẠI
# ====================================
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        phone = request.form.get('phone', '').strip()
        
        # Tìm user theo số điện thoại (giả sử bạn đã thêm trường phone vào model User)
        user = User.query.filter_by(phone=phone).first()
        
        if not user:
            flash('Số điện thoại không tồn tại trong hệ thống!', 'error')
            return redirect(url_for('forgot_password'))
        
        # Tạo mã OTP ngẫu nhiên (6 số) và lưu vào session
        import random
        otp = str(random.randint(100000, 999999))
        session['reset_otp'] = otp
        session['reset_phone'] = phone
        session['reset_user_id'] = user.id
        
        # TODO: Gửi OTP qua SMS (sử dụng Twilio, Viettel, hoặc dịch vụ khác)
        # Hiện tại chỉ flash OTP để test (xóa khi deploy thật)
        flash(f'Mã OTP của bạn là: {otp} (chỉ dùng để test)', 'info')
        flash('Mã OTP đã được gửi đến số điện thoại của bạn!', 'success')
        
        return redirect(url_for('verify_otp'))
    
    return render_template('forgot_password.html')

# ====================================
# QUÊN MẬT KHẨU - BƯỚC 2: NHẬP OTP
# ====================================
@app.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    if 'reset_otp' not in session:
        flash('Phiên đặt lại mật khẩu đã hết hạn!', 'error')
        return redirect(url_for('forgot_password'))
    
    if request.method == 'POST':
        user_otp = request.form.get('otp', '').strip()
        
        if user_otp == session['reset_otp']:
            # OTP đúng → cho phép đặt lại mật khẩu
            session['reset_verified'] = True
            flash('Xác thực OTP thành công! Hãy đặt mật khẩu mới.', 'success')
            return redirect(url_for('reset_password'))
        else:
            flash('Mã OTP không đúng!', 'error')
    
    return render_template('verify_otp.html')

# ====================================
# QUÊN MẬT KHẨU - BƯỚC 3: ĐẶT LẠI MẬT KHẨU MỚI
# ====================================
@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if 'reset_verified' not in session or not session['reset_verified']:
        flash('Phiên đặt lại mật khẩu không hợp lệ!', 'error')
        return redirect(url_for('forgot_password'))
    
    if request.method == 'POST':
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        
        if not password or len(password) < 6:
            flash('Mật khẩu phải có ít nhất 6 ký tự!', 'error')
            return redirect(url_for('reset_password'))
        
        if password != confirm_password:
            flash('Mật khẩu xác nhận không khớp!', 'error')
            return redirect(url_for('reset_password'))
        
        # Cập nhật mật khẩu mới
        user = User.query.get(session['reset_user_id'])
        user.password = generate_password_hash(password)
        
        db.session.commit()
        
        # Xóa session reset
        session.pop('reset_otp', None)
        session.pop('reset_phone', None)
        session.pop('reset_user_id', None)
        session.pop('reset_verified', None)
        
        flash('Đặt lại mật khẩu thành công! Hãy đăng nhập lại.', 'success')
        return redirect(url_for('login'))
    
    return render_template('reset_password.html')

# ĐỔI EMAIL
@app.route('/profile/change-email', methods=['POST'])
@login_required
def change_email():
    data = request.get_json()
    new_email = data.get('new_email', '').strip().lower()
    current_password = data.get('current_password', '')
    
    # Kiểm tra mật khẩu hiện tại
    if not check_password_hash(current_user.password, current_password):
        return jsonify({'error': 'Mật khẩu hiện tại không đúng!'}), 400
    
    # Kiểm tra email mới đã tồn tại chưa
    existing_user = User.query.filter_by(email=new_email).first()
    if existing_user and existing_user.id != current_user.id:
        return jsonify({'error': 'Email này đã được sử dụng!'}), 400
    
    # Cập nhật email
    current_user.email = new_email
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Đổi email thành công!'})

# ĐỔI MẬT KHẨU
@app.route('/profile/change-password', methods=['POST'])
@login_required
def change_password():
    data = request.get_json()
    current_password = data.get('current_password', '')
    new_password = data.get('new_password', '')
    
    # Kiểm tra mật khẩu hiện tại
    if not check_password_hash(current_user.password, current_password):
        return jsonify({'error': 'Mật khẩu hiện tại không đúng!'}), 400
    
    # Kiểm tra độ dài mật khẩu mới
    if len(new_password) < 6:
        return jsonify({'error': 'Mật khẩu mới phải có ít nhất 6 ký tự!'}), 400
    
    # Cập nhật mật khẩu
    current_user.password = generate_password_hash(new_password)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Đổi mật khẩu thành công!'})

# ====================================
# DANH SÁCH CHUYÊN GIA - CHO NGƯỜI DÙNG THƯỜNG
# ====================================
@app.route('/experts')
def experts_list():
    """Hiển thị danh sách tất cả chuyên gia"""
    # Lấy danh sách chuyên gia đã được xác minh, không phải admin
    experts = User.query.filter(
        User.is_verified_expert == True,
        User.role != 'admin'
    ).all()
    
    # Thêm thông tin thống kê cho mỗi chuyên gia
    for expert in experts:
        expert.total_posts = expert.posts.filter_by(is_expert_post=True).count()
        expert.total_consultations = TimeSlot.query.filter_by(
            expert_id=expert.id,
            status='booked'
        ).count()
        
    return render_template('experts_list.html', experts=experts)

# ====================================
# XEM CHI TIẾT CHUYÊN GIA + LỊCH TƯ VẤN
# ====================================
@app.route('/expert/<int:expert_id>/profile')
def expert_public_profile(expert_id):
    """Xem hồ sơ công khai của chuyên gia + lịch tư vấn"""
    expert = User.query.get_or_404(expert_id)
    
    if not expert.is_verified_expert:
        flash('Người này không phải chuyên gia!', 'error')
        return redirect(url_for('home'))
    
    # Lấy khung giờ còn trống trong tương lai
    now = vietnam_now()
    available_slots = TimeSlot.query.filter_by(
        expert_id=expert_id,
        status='available'
    ).filter(
        TimeSlot.start_time >= now
    ).order_by(TimeSlot.start_time).all()
    
    # Nhóm theo ngày
    slots_by_date = {}
    for slot in available_slots:
        date_key = slot.start_time.strftime('%Y-%m-%d')
        if date_key not in slots_by_date:
            slots_by_date[date_key] = []
        slots_by_date[date_key].append(slot)
    
    # Lấy bài viết tư vấn gần đây
    recent_posts = Post.query.filter_by(
        user_id=expert_id,
        is_expert_post=True
    ).order_by(Post.created_at.desc()).limit(5).all()
    
    # Thống kê
    stats = {
        'total_posts': expert.posts.filter_by(is_expert_post=True).count(),
        'total_consultations': TimeSlot.query.filter_by(
            expert_id=expert_id,
            status='booked'
        ).count(),
        'followers': expert.followers.count(),
        'rating': 4.8  # Tạm thời hardcode, sau có thể tính từ feedback
    }
    
    return render_template(
        'expert_public_profile.html',
        expert=expert,
        available_slots=available_slots,
        slots_by_date=slots_by_date,
        recent_posts=recent_posts,
        stats=stats
    )

# === CHẠY APP ===
if __name__ == '__main__':
    with app.app_context():
        # Đảm bảo tất cả các bảng được tạo
        db.create_all()

    socketio.run(app, debug=True, port=5000, use_reloader=False)
    # KHÔNG DÙNG app.run()!