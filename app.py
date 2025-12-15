import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, url_for
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from flask_socketio import SocketIO, join_room, emit
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_migrate import Migrate
from database import db, init_app
from models import User, Post, Comment, Follow, FriendRequest, Notification, Report, ExpertRequest, Message
from config import Config
import os
from datetime import datetime, timedelta
from sqlalchemy.orm import joinedload
from markupsafe import Markup
from sqlalchemy import func
import base64   
import time

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


# === KHỞI TẠO DB ===
def init_db():
    with app.app_context():
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


# === HÀM HỖ TRỢ ===
def get_friends(user):
    """Lấy danh sách bạn bè (đã follow 2 chiều)"""
    # Người mình follow
    following = {f.followed_id for f in Follow.query.filter_by(follower_id=user.id).all()}
    # Người follow mình
    followers = {f.follower_id for f in Follow.query.filter_by(followed_id=user.id).all()}
    # Giao nhau = bạn bè thật sự
    friend_ids = following.intersection(followers)
    return User.query.filter(User.id.in_(friend_ids)).order_by(User.name).all()

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
    query = Post.query.order_by(Post.created_at.desc())
    if category != 'all':
        query = query.filter_by(category=category)
    posts = query.limit(20).all()

    categories = ['all', 'health', 'nutrition', 'story', 'tips', 'other']
    category_names = {
        'all': 'Tất cả', 'health': 'Sức khỏe', 'nutrition': 'Dinh dưỡng',
        'story': 'Tâm sự', 'tips': 'Mẹo hay', 'other': 'Khác'
    }

    friends = get_friends(current_user) if current_user.is_authenticated else []
    suggested_users = get_suggested_users(current_user) if current_user.is_authenticated else []

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
@app.route('/like/<int:post_id>')
@login_required
def like(post_id):
    post = Post.query.get_or_404(post_id)
    post.likes += 1
    current_user.points += 1

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
    return jsonify({'likes': post.likes, 'points': current_user.points})

# COMMENT
@app.route('/comment/<int:post_id>', methods=['POST'])
@login_required
def comment(post_id):
    post = Post.query.get_or_404(post_id)
    content = request.form.get('content', '').strip()
    if not content:
        return jsonify({'error': 'Nội dung bình luận trống!'}), 400

    comment_obj = Comment(content=content, user_id=current_user.id, post_id=post_id)
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

        # Lưu danh sách ảnh dưới dạng chuỗi
        post = Post(
            title=title,
            content=content,
            category=category,
            images=','.join(images_list) if images_list else None,
            video=video_file,
            user_id=current_user.id
        )
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
    """Lấy danh sách lời mời đang chờ (người follow mình nhưng mình chưa follow lại)"""
    # Tất cả người đã follow mình
    incoming = Follow.query.filter_by(followed_id=user.id).all()
    pending = []
    
    for follow in incoming:
        # Nếu mình chưa follow lại → vẫn là pending
        if not Follow.query.filter_by(follower_id=user.id, followed_id=follow.follower_id).first():
            pending.append(follow)
    
    return pending

@app.route('/friends')
@login_required
def friends():
    friends_list = current_user.friends

    pending_requests = FriendRequest.query.filter_by(
        recipient_id=current_user.id
    ).all()

    friend_ids = [u.id for u in friends_list]

    suggested_users = User.query.filter(
        User.id != current_user.id,
        ~User.id.in_(friend_ids)
    ).order_by(func.random()).limit(10).all()

    return render_template(
        'friends.html',
        friends=friends_list,
        pending_requests=pending_requests,
        suggested_users=suggested_users
    )



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
    notifs = (
        Notification.query
        .filter_by(user_id=current_user.id)
        .options(joinedload(Notification.related_user))
        .order_by(Notification.created_at.desc())
        .all()
    )

    results = []
    for n in notifs:
        if n.related_user and n.related_user.avatar:
            # avatar đã là 'uploads/xxx.jpg'
            avatar_path = n.related_user.avatar.replace('\\', '/').lstrip('/')
        else:
            avatar_path = 'static/default.jpg'

        avatar_url = url_for('static', filename=avatar_path)

        results.append({
            "id": n.id,
            "title": n.title,
            "message": n.message,
            "is_read": n.is_read,
            "created_at": n.created_at.strftime('%H:%M %d/%m/%Y'),
            "related_user_avatar": avatar_url
        })

    return jsonify(results)




@app.route('/notifications/count')
@login_required
def notification_count():
    count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return jsonify({'count': count})

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
        flash('Chỉ chuyên gia mới đăng được!', 'error')
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

    return render_template(
        'admin_dashboard.html',
        stats=stats,
        users=users,
        expert_requests=expert_requests,
        reports=reports
    )

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

@app.route('/post/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    if current_user.role != 'admin':
        flash('Bạn không có quyền xóa bài!', 'error')
        return redirect(url_for('home'))

    post = Post.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    flash('Đã xóa bài viết!', 'success')
    return redirect(url_for('admin_dashboard'))

from flask_login import login_required, current_user


# === GỬI LỜI MỜI KẾT BẠN ===
@app.route('/send_friend_request/<int:user_id>', methods=['POST'])
@login_required
def send_friend_request(user_id):
    recipient = User.query.get_or_404(user_id)
    if recipient.id == current_user.id:
        flash('Không thể gửi lời mời cho chính mình!', 'warning')
        return redirect(url_for('friends'))
    
    # Kiểm tra đã là bạn bè chưa
    if get_friends(current_user).filter_by(id=recipient.id).first():
        flash('Đã là bạn bè rồi!', 'warning')
        return redirect(url_for('friends'))
    
    # Kiểm tra đã gửi request chưa
    existing_request = FriendRequest.query.filter_by(
        sender_id=current_user.id, 
        recipient_id=recipient.id
    ).first()
    
    if not existing_request:
        request = FriendRequest(sender_id=current_user.id, recipient_id=recipient.id)
        db.session.add(request)
        db.session.commit()
        flash(f'Đã gửi lời mời kết bạn tới {recipient.name}!', 'success')
    else:
        flash('Đã gửi lời mời trước đó!', 'warning')
    
    return redirect(url_for('friends'))


# === CHẤP NHẬN LỜI MỜI KẾT BẠN ===
@app.route('/accept_friend_request/<int:user_id>', methods=['POST'])
@login_required
def accept_friend_request(user_id):
    incoming = Follow.query.filter_by(follower_id=user_id, followed_id=current_user.id).first()
    if not incoming:
        flash('Không có lời mời kết bạn!', 'danger')
        return redirect(url_for('friends'))

    # KIỂM TRA ĐÃ LÀ BẠN CHƯA
    existing = Follow.query.filter_by(follower_id=current_user.id, followed_id=user_id).first()
    if existing:
        flash('Bạn đã là bạn bè rồi!', 'warning')
        return redirect(url_for('friends'))

    # Tạo quan hệ ngược lại
    db.session.add(Follow(follow(follower_id=current_user.id, followed_id=user_id)))
    db.session.commit()
    flash(f'Đã kết bạn với {User.query.get(user_id).name}!', 'success')
    return redirect(url_for('friends'))


# === TỪ CHỐI LỜI MỜI ===
@app.route('/reject_friend_request/<int:user_id>', methods=['POST'])
@login_required
def reject_friend_request(user_id):
    follow = Follow.query.filter_by(follower_id=user_id, followed_id=current_user.id).first()
    if follow:
        db.session.delete(follow)
        db.session.commit()
        flash('Đã từ chối lời mời.', 'info')
    return redirect(url_for('friends'))

# === CHAT ROUTE ===
@app.route('/chat/<int:user_id>')
@login_required
def chat(user_id):
    if not is_friend(current_user.id, user_id):
        return render_template('not_friend.html', other_id=user_id)
    other_user = User.query.get_or_404(user_id)
    return render_template('chat.html', other_user=other_user)

# === HÀM KIỂM TRA BẠN BÈ ===
def is_friend(user1_id, user2_id):
    f1 = Follow.query.filter_by(follower_id=user1_id, followed_id=user2_id).first()
    f2 = Follow.query.filter_by(follower_id=user2_id, followed_id=user1_id).first()
    return f1 and f2



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

    timestamp = datetime.now().strftime('%H:%M %d/%m')
    sender = User.query.get(sender_id)

    message_data = {
        'sender_id': sender_id,
        'sender_name': sender.name,
        'content': content,
        'timestamp': timestamp
    }

    room = f"chat_{min(sender_id, receiver_id)}_{max(sender_id, receiver_id)}"
    
    # THAY ĐỔI QUAN TRỌNG: thêm include_self=True và broadcast=True
    emit('receive_message', message_data, room=room, include_self=True, broadcast=True)
    print(f"✅ Sent to room {room}: {content}")

# @app.route('/chat/history/<int:friend_id>')
# def chat_history(friend_id):
#     from flask_login import current_user
    
#     print(f"🔍 Auth status: {current_user.is_authenticated}")
#     print(f"🔍 Current user: {current_user if current_user.is_authenticated else 'Anonymous'}")
    
#     if not current_user.is_authenticated:
#         return jsonify([])  # ← TRẢ ARRAY RỖNG THAY VÌ 401
    
#     messages = Message.query.filter(
#         ((Message.sender_id == current_user.id) & (Message.receiver_id == friend_id)) |
#         ((Message.sender_id == friend_id) & (Message.receiver_id == current_user.id))
#     ).order_by(Message.timestamp.asc()).all()

#     return jsonify([{
#         'sender_id': m.sender_id,
#         'sender_name': m.sender.name,
#         'content': m.content,
#         'timestamp': m.timestamp.strftime('%H:%M %d/%m')
#     } for m in messages])

@app.template_filter('nl2br')
def nl2br_filter(s):
    """Chuyển line break (\n) thành <br> trong HTML"""
    if not s:
        return ''
    return Markup(s.replace('\n', '<br>\n'))

@app.route('/rate/<int:post_id>', methods=['POST'])
@login_required
def rate_post(post_id):
    post = Post.query.get_or_404(post_id)
    data = request.get_json()
    stars = data.get('stars', 0)
    if stars < 1 or stars > 5:
        return jsonify({'error': 'Sao phải từ 1-5'}), 400
    
    # Giả sử bạn thêm field rating và rating_count vào model Post
    if not hasattr(post, 'rating'):
        post.rating = 0
        post.rating_count = 0
    
    post.rating = ((post.rating * post.rating_count) + stars) / (post.rating_count + 1)
    post.rating_count += 1
    db.session.commit()
    
    return jsonify({'success': True})

# ============================================
# SOCKET EVENTS CHO VIDEO CALL
# ============================================

@socketio.on('join_chat')
def on_join_chat(data):
    user_id = data['user_id']
    friend_id = data['friend_id']
    
    # Join room chat
    room = f"chat_{min(user_id, friend_id)}_{max(user_id, friend_id)}"
    join_room(room)
    
    # Join room riêng cho user (để nhận video call)
    join_room(f"user_{user_id}")
    
    print(f"✅ User {user_id} joined room {room} and user_{user_id}")

@socketio.on('send_message')
def handle_message(data):
    sender_id = data['sender_id']
    receiver_id = data['receiver_id']
    content = data.get('content', '').strip()
    msg_type = data.get('type', 'text')
    filename = data.get('filename', None)
    
    if not content or sender_id == receiver_id:
        return

    # XỬ LÝ FILE (IMAGE, VIDEO, AUDIO)
    if msg_type in ['image', 'video', 'audio']:
        try:
            # Decode base64
            if ',' in content:
                file_data = content.split(',')[1]
            else:
                file_data = content
                
            file_bytes = base64.b64decode(file_data)
            
            # Tạo tên file duy nhất
            extension_map = {
                'image': 'jpg',
                'video': 'mp4',
                'audio': 'webm'
            }
            ext = extension_map.get(msg_type, 'dat')
            filename = f"{sender_id}_{int(time.time())}.{ext}"
            
            # Lưu file vào thư mục uploads
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            with open(filepath, 'wb') as f:
                f.write(file_bytes)
            
            # Cập nhật content thành đường dẫn file
            content = f'/static/uploads/{filename}'
            
            print(f"✅ Saved {msg_type} file: {filename}")
            
        except Exception as e:
            print(f"❌ Error saving file: {e}")
            return

    # Lưu vào DB
    msg = Message(
        sender_id=sender_id, 
        receiver_id=receiver_id, 
        content=content,
        type=msg_type
    )
    db.session.add(msg)
    db.session.commit()

    timestamp = datetime.now().strftime('%H:%M %d/%m')
    sender = User.query.get(sender_id)

    message_data = {
        'sender_id': sender_id,
        'sender_name': sender.name,
        'content': content,
        'timestamp': timestamp,
        'type': msg_type
    }

    room = f"chat_{min(sender_id, receiver_id)}_{max(sender_id, receiver_id)}"
    emit('receive_message', message_data, room=room, include_self=True, broadcast=True)
    print(f"✅ Sent {msg_type} to room {room}")


# ============================================
# VIDEO CALL SOCKET EVENTS
# ============================================

@socketio.on('video_call_request')
def handle_call_request(data):
    """Xử lý yêu cầu gọi video"""
    from_user = data['from']
    to_user = data['to']
    caller_name = data['caller_name']
    
    print(f"📞 Video call from {from_user} to {to_user}")
    
    # Gửi thông báo cuộc gọi đến người nhận
    emit('video_call_request', {
        'from': from_user,
        'caller_name': caller_name
    }, room=f"user_{to_user}")


@socketio.on('video_call_accepted')
def handle_call_accepted(data):
    """Xử lý khi chấp nhận cuộc gọi"""
    from_user = data['from']
    to_user = data['to']
    
    print(f"✅ Call accepted: {from_user} -> {to_user}")
    
    emit('video_call_accepted', data, room=f"user_{to_user}")


@socketio.on('video_call_rejected')
def handle_call_rejected(data):
    """Xử lý khi từ chối cuộc gọi"""
    from_user = data['from']
    to_user = data['to']
    
    print(f"❌ Call rejected: {from_user} -> {to_user}")
    
    emit('video_call_rejected', {}, room=f"user_{to_user}")


@socketio.on('video_call_offer')
def handle_offer(data):
    """Xử lý WebRTC offer"""
    to_user = data['to']
    offer = data['offer']
    
    print(f"📤 Sending offer to user {to_user}")
    
    emit('video_call_offer', {
        'from': data.get('from'),
        'offer': offer
    }, room=f"user_{to_user}")


@socketio.on('video_call_answer')
def handle_answer(data):
    """Xử lý WebRTC answer"""
    to_user = data['to']
    answer = data['answer']
    
    print(f"📥 Sending answer to user {to_user}")
    
    emit('video_call_answer', {
        'from': data.get('from'),
        'answer': answer
    }, room=f"user_{to_user}")


@socketio.on('ice_candidate')
def handle_ice_candidate(data):
    """Xử lý ICE candidate cho WebRTC"""
    to_user = data['to']
    candidate = data['candidate']
    
    emit('ice_candidate', {
        'candidate': candidate
    }, room=f"user_{to_user}")


@socketio.on('call_ended')
def handle_call_ended(data):
    """Xử lý khi kết thúc cuộc gọi"""
    to_user = data['to']
    
    print(f"☎️ Call ended with user {to_user}")
    
    emit('call_ended', {}, room=f"user_{to_user}")


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

# === CHẠY APP ===
if __name__ == '__main__':
    init_db()  # Tự động tạo admin khi chạy lần đầu
    with app.app_context():
        db.create_all()  # Đảm bảo bảng tồn tại
    socketio.run(app, debug=True, port=5000, use_reloader=False)
    # KHÔNG DÙNG app.run()!


# # app.py – CUỐI FILE
# from database import db, init_app

# app = Flask(__name__)
# # ... config

# init_app(app)  # Khởi tạo db với app