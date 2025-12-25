# app.py
import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
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
    return User.query.get(int(id))

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
            return redirect(url_for('home'))
        flash('Email hoặc mật khẩu sai!', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

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
        current_user.points -= 1
        liked = False
    else:
        # Like
        new_like = PostLike(user_id=current_user.id, post_id=post_id)
        db.session.add(new_like)
        post.likes += 1
        current_user.points += 1
        liked = True
        
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
@app.route('/comment/<int:post_id>', methods=['POST'])
@login_required
def comment(post_id):
    post = Post.query.get_or_404(post_id)
    content = request.form.get('content', '').strip()
    if not content:
        return jsonify({'error': 'Nội dung bình luận trống!'}), 400

    comment_obj = Comment(content=content, user_id=current_user.id, post_id=post_id)
    
    # ✅ GÁN THỜI GIAN MỘT CÁCH TƯỜNG MINH
    comment_obj.created_at = vietnam_now()
    
    db.session.add(comment_obj)
    post.comments_count += 1

    if post.author.id != current_user.id:
        notif = Notification(
            user_id=post.author.id,
            title="Bình luận mới!",
            message=f"{current_user.name} đã bình luận: \"{content[:50]}{'...' if len(content)>50 else ''}\"",
            type='comment',
            related_id=post.id,
            related_user_id=current_user.id
        )
        # ✅ Cả thông báo cũng nên có giờ đúng
        notif.created_at = vietnam_now()
        db.session.add(notif)

    db.session.commit()
    return jsonify({'success': True, 'comments_count': post.comments_count})

# LẤY BÌNH LUẬN (CHO MODAL)
@app.route('/comments/<int:post_id>')
def get_comments(post_id):
    post = Post.query.get_or_404(post_id)
    comments = Comment.query.filter_by(post_id=post_id).order_by(Comment.created_at).all()
    return jsonify([{
        'id': c.id,
        'content': c.content,
        'created_at': c.created_at.strftime('%H:%M %d/%m'),
        'author': {
            'name': c.author.name,
            'avatar': c.author.avatar or 'default.jpg'
        }
    } for c in comments])

# PROFILE
@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        current_user.name = request.form['name'].strip()
        current_user.bio = request.form.get('bio', '').strip()
        
        if 'avatar' in request.files:
            file = request.files['avatar']
            if file and file.filename:
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                current_user.avatar = f'uploads/{filename}'
        
        db.session.commit()
        flash('Cập nhật hồ sơ thành công!', 'success')
    
    return render_template('profile.html', user=current_user)

# ĐĂNG BÀI
@app.route('/post', methods=['GET', 'POST'])
@login_required
def create_post():
    if request.method == 'POST':
        title = request.form['title'].strip()
        content = request.form['content'].strip()
        category = request.form.get('category', 'other')

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
            user_id=current_user.id
        )
        
        # ✅ BỎ COMMENT DÒNG NÀY
        post.created_at = vietnam_now()
        
        db.session.add(post)
        db.session.commit()

        flash('Đăng bài thành công!', 'success')
        return redirect(url_for('home'))

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

    # Kiểm tra đã báo cáo chưa
    existing = Report.query.filter_by(post_id=post_id, user_id=current_user.id).first()
    if existing:
        return jsonify({'error': 'Bạn đã báo cáo bài viết này rồi!'}), 400

    # Tạo báo cáo
    report = Report(post_id=post_id, user_id=current_user.id, reason=reason)
    db.session.add(report)
    db.session.commit()

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
    # Nếu đã là chuyên gia → chuyển về trang chủ
    if current_user.is_verified_expert:
        flash('Bạn đã là chuyên gia!', 'info')
        return redirect(url_for('home'))

    if request.method == 'POST':
        reason = request.form.get('reason', '').strip()
        category = request.form.get('category')
        file = request.files.get('certificate')

        if not reason or not category:
            flash('Vui lòng điền đầy đủ thông tin!', 'danger')
            return render_template('expert_request.html')

        filename = None
        if file and file.filename:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            filename = f'uploads/{filename}'

        # Tạo yêu cầu
        req = ExpertRequest(
            user_id=current_user.id,
            reason=reason,
            certificate=filename,
            status='pending'
        )
        db.session.add(req)
        db.session.commit()

        flash('Đã gửi yêu cầu trở thành chuyên gia! Chờ duyệt.', 'success')
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
        flash('Bạn không có quyền!', 'error')
        return redirect(url_for('home'))

    req = ExpertRequest.query.get_or_404(req_id)

    if action == 'approve':
        req.user.is_verified_expert = True
        req.status = 'approved'
        req.user.points += 100  # Thưởng điểm
        flash(f'Đã duyệt chuyên gia: {req.user.name}', 'success')
    elif action == 'reject':
        req.status = 'rejected'
        flash(f'Đã từ chối yêu cầu của {req.user.name}', 'info')
    else:
        flash('Hành động không hợp lệ!', 'error')
        return redirect(url_for('admin_dashboard'))

    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/user/edit', methods=['POST'])
@login_required
def admin_edit_user():
    if current_user.role != 'admin':
        return jsonify({'error': 'Không có quyền!'}), 403

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
            user.avatar = f"uploads/{filename}"  # ← SỬA DÒNG NÀY: THÊM "uploads/"

    db.session.commit()
    return jsonify({'success': True})

# ---------- QUẢN LÝ BÀI VIẾT ----------
@app.route('/admin/post/<int:post_id>/comments')
@login_required
def admin_post_comments(post_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Không có quyền'}), 403
    post = Post.query.get_or_404(post_id)
    comments = [{
        'id': c.id,
        'author': c.author.name,
        'content': c.content,
        'created_at': c.created_at.strftime('%d/%m %H:%M')
    } for c in post.comments]
    return jsonify({'comments': comments})

@app.route('/admin/post/<int:post_id>/delete', methods=['POST'])
@login_required
def admin_delete_post(post_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Không có quyền'}), 403
    post = Post.query.get_or_404(post_id)
    try:
        db.session.delete(post)
        db.session.commit()
        return jsonify({'success': True})
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

# Sửa lại route admin_dashboard để truyền thêm posts
@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Bạn không có quyền truy cập!', 'error')
        return redirect(url_for('home'))

    stats = {
        'total_users': User.query.count(),
        'total_posts': Post.query.count(),
        'total_experts': User.query.filter_by(is_verified_expert=True).count(),
        'total_points': db.session.query(db.func.sum(User.points)).scalar() or 0
    }

    users = User.query.order_by(User.id.desc()).all()
    expert_requests = ExpertRequest.query.filter_by(status='pending').all()
    reports = Report.query.order_by(Report.created_at.desc()).all()
    posts = Post.query.order_by(Post.created_at.desc()).all()  # THÊM DÒNG NÀY

    return render_template(
        'admin_dashboard.html',
        stats=stats,
        users=users,
        expert_requests=expert_requests,
        reports=reports,
        posts=posts   # THÊM DÒNG NÀY
    )

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

# === CHẠY APP ===
if __name__ == '__main__':
    with app.app_context():
        # Đảm bảo tất cả các bảng được tạo
        db.create_all()
        
        # Tạo admin nếu chưa có
        if not User.query.filter_by(email='admin@momconnect.com').first():
            hashed = generate_password_hash('admin123')
            admin = User(
                name='Admin MomConnect',
                email='admin@momconnect.com',
                password=hashed,
                role='admin',
                points=9999,
                is_verified_expert=True
            )
            db.session.add(admin)
            db.session.commit()
            print("ĐÃ TẠO TÀI KHOẢN ADMIN:")
            print("Email: admin@momconnect.com")
            print("Mật khẩu: admin123")

    socketio.run(app, debug=True, port=5000, use_reloader=False)
    # KHÔNG DÙNG app.run()!