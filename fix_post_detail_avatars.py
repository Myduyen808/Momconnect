# Script sửa avatar trong post_detail.html
# Thay thế avatar_url bằng url_for để đồng bộ với hệ thống

import os
import re

def fix_post_detail_avatars():
    """Sửa tất cả avatar trong post_detail.html"""
    
    print("🔧 SỬA AVATAR TRONG POST_DETAIL.HTML")
    print("="*50)
    
    post_detail_file = 'post_detail.html'
    
    if not os.path.exists(post_detail_file):
        print(f"❌ Không tìm thấy file {post_detail_file}")
        print("📝 Đảm bảo bạn đang ở thư mục chứa file post_detail.html")
        return False
    
    # Đọc file
    with open(post_detail_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Đếm số avatar cần sửa
    avatar_count = content.count('avatar_url')
    print(f"📊 Tìm thấy {avatar_count} avatar_url cần sửa")
    
    # Thay thế tất cả avatar_url bằng url_for
    replacements = [
        # 1. Avatar tác giả bài viết
        (
            r'src="\{\{\s*post\.author\.avatar_url\s*\}\}"',
            'src="{{ url_for(\'static\', filename=post.author.avatar or \'images/default-avatar.png\') }}"'
        ),
        # 2. Avatar current_user trong form bình luận
        (
            r'src="\{\{\s*current_user\.avatar_url\s*\}\}"',
            'src="{{ url_for(\'static\', filename=current_user.avatar or \'images/default-avatar.png\') }}"'
        ),
        # 3. Avatar tác giả bình luận
        (
            r'src="\{\{\s*comment\.author\.avatar_url\s*\}\}"',
            'src="{{ url_for(\'static\', filename=comment.author.avatar or \'images/default-avatar.png\') }}"'
        )
    ]
    
    changes_made = []
    
    for i, (pattern, replacement) in enumerate(replacements):
        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content)
            changes_made.append(f"✅ Sửa avatar {i+1}")
    
    # Ghi lại file
    with open(post_detail_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    if changes_made:
        print(f"✅ Đã sửa {len(changes_made)} avatar trong post_detail.html")
        for change in changes_made:
            print(f"  {change}")
    else:
        print("⚠️ Không tìm thấy avatar_url cần sửa")
    
    return True

def create_post_detail_fixed():
    """Tạo file post_detail.html đã sửa sẵn"""
    
    print("\n📝 TẠO FILE POST_DETAIL.HTML ĐÃ SỬA")
    print("-"*40)
    
    fixed_content = '''{% extends "base.html" %}
{% block title %}{{ post.title }}{% endblock %}

{% block content %}
<div class="max-w-4xl mx-auto p-6">
    <div class="bg-white rounded-3xl shadow-2xl overflow-hidden">
        <!-- Header bài viết -->
        <div class="p-8 border-b border-gray-100">
            <div class="flex items-start justify-between mb-6">
                <div class="flex items-center gap-4">
                    <!-- ✅ SỬA AVATAR TÁC GIẢ -->
                    <img src="{{ url_for('static', filename=post.author.avatar or 'images/default-avatar.png') }}"
                        class="w-16 h-16 rounded-full object-cover ring-4 ring-pink-200 shadow-lg">
                    <div>
                        <h3 class="text-2xl font-bold text-gray-900">{{ post.author.name }}</h3>
                        <p class="text-sm text-gray-500 flex items-center gap-2 mt-1">
                            <i class="far fa-clock"></i>
                        {{ post.created_at | vietnam_time }}
                            {% if post.is_expert_post %}
                            <span class="ml-3 bg-gradient-to-r from-purple-500 to-blue-600 text-white px-3 py-1 rounded-full text-xs font-bold">
                                <i class="fas fa-stethoscope mr-1"></i> Tư vấn chuyên gia
                            </span>
                            {% endif %}
                        </p>
                    </div>
                </div>

                <!-- Menu 3 chấm -->
                <div class="relative">
                    <button onclick="toggleMenu({{ post.id }})" class="p-3 hover:bg-gray-100 rounded-full transition">
                        <i class="fas fa-ellipsis-h text-gray-600 text-xl"></i>
                    </button>
                    <div id="menu-{{ post.id }}" class="hidden absolute right-0 mt-2 w-56 bg-white rounded-xl shadow-xl border z-30">
                        <button onclick="reportPost({{ post.id }})" class="w-full text-left px-5 py-3 hover:bg-gray-50 flex items-center gap-3 text-red-600">
                            <i class="fas fa-flag"></i> Báo cáo bài viết
                        </button>
                        {% if current_user.id == post.user_id or current_user.role == 'admin' %}
                        <button onclick="deletePost({{ post.id }})" class="w-full text-left px-5 py-3 hover:bg-red-50 flex items-center gap-3 text-red-600">
                            <i class="fas fa-trash"></i> Xóa bài viết
                        </button>
                        {% endif %}
                    </div>
                </div>
            </div>

            <!-- Tiêu đề -->
            <h1 class="text-4xl font-bold text-gray-900 mb-4">{{ post.title }}</h1>

            <!-- Chủ đề -->
            <div class="flex items-center gap-3 mb-6">
                <span class="px-4 py-2 rounded-full text-sm font-medium
                    {% if post.category == 'health' %}bg-green-100 text-green-700
                    {% elif post.category == 'nutrition' %}bg-yellow-100 text-yellow-700
                    {% elif post.category == 'story' %}bg-purple-100 text-purple-700
                    {% elif post.category == 'tips' %}bg-blue-100 text-blue-700
                    {% else %}bg-gray-100 text-gray-700{% endif %}">
                    {{ {'health': 'Sức khỏe', 'nutrition': 'Dinh dưỡng', 'story': 'Tâm sự', 'tips': 'Mẹo hay', 'other': 'Khác'}[post.category] }}
                </span>
            </div>

            <!-- Nội dung -->
            <div class="prose max-w-none text-gray-700 leading-relaxed text-lg mb-8">
                {{ post.content | replace('\\n', '<br>') | safe }}
            </div>

            <!-- Media: Nhiều ảnh + Video -->
            {% if post.get_images_list() or post.video %}
            <div class="mb-8 -mx-8">
                <!-- Nhiều ảnh -->
                {% if post.get_images_list() %}
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 px-8">
                    {% for img in post.get_images_list() %}
                    <div class="relative group overflow-hidden rounded-2xl shadow-lg bg-gray-100">
                        <img src="{{ url_for('static', filename='uploads/' ~ img) }}" alt="Ảnh bài viết"
                            class="w-full h-80 object-cover hover:scale-110 transition duration-500 cursor-pointer">
                        <div class="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-20 transition"></div>
                    </div>
                    {% endfor %}
                </div>
                {% endif %}

                <!-- Video -->
                {% if post.video %}
                <div class="px-8 mt-6">
                    <div class="relative rounded-2xl overflow-hidden shadow-2xl bg-black">
                        <video controls class="w-full h-96 object-cover">
                            <source src="{{ url_for('static', filename='uploads/' ~ post.video) }}" type="video/mp4">
                            Trình duyệt của bạn không hỗ trợ video.
                        </video>
                        <div class="absolute top-4 left-4">
                            <span class="bg-red-600 text-white px-3 py-1 rounded-full text-sm font-bold flex items-center gap-2">
                                <i class="fas fa-play-circle"></i> Video
                            </span>
                        </div>
                    </div>
                </div>
                {% endif %}
            </div>
            {% endif %}

            <!-- Hành động: Thích + Bình luận -->
            <div class="flex items-center justify-between p-6 border-b border-gray-100">
                <div class="flex items-center gap-8">
                    <button onclick="likePost({{ post.id }})" class="flex items-center gap-3 px-6 py-3 bg-gradient-to-r from-pink-100 to-purple-100 rounded-full hover:shadow-lg transition group">
                        <i class="fas fa-heart text-2xl text-pink-600 group-hover:scale-110 transition"></i>
                        <span class="font-bold text-pink-700">Thích • {{ post.likes }}</span>
                    </button>

                    <button onclick="focusCommentInput()" class="flex items-center gap-3 px-6 py-3 bg-gray-100 rounded-full hover:bg-gray-200 transition">
                        <i class="fas fa-comment text-2xl text-blue-600"></i>
                        <span class="font-bold text-gray-700">Bình luận • {{ post.comments_count }}</span>
                    </button>
                </div>

                <!-- Đánh giá sao -->
                <div class="flex items-center gap-2">
                    <span class="text-lg font-medium text-gray-700">Đánh giá bài viết:</span>
                    <div class="flex items-center gap-1">
                        {% for i in range(1, 6) %}
                        <button onclick="ratePost({{ post.id }}, {{ i }})" class="text-3xl hover:scale-125 transition {% if i <= (post.rating|default(0)) %}text-yellow-400{% else %}text-gray-300{% endif %}">
                            ★
                        </button>
                        {% endfor %}
                    </div>
                    <span class="text-sm text-gray-600">({{ post.rating_count|default(0) }} đánh giá)</span>
                </div>
            </div>
        </div>

        <!-- Form bình luận -->
        <div class="p-6 bg-gray-50">
            <div class="flex gap-4">
                <!-- ✅ SỬA AVATAR CURRENT_USER -->
                <img src="{{ url_for('static', filename=current_user.avatar or 'images/default-avatar.png') }}"
                    class="w-12 h-12 rounded-full ring-4 ring-white shadow">
                <div class="flex-1">
                    <textarea id="comment-input" rows="3" placeholder="Viết bình luận của bạn..."
                        class="w-full px-5 py-4 border border-gray-300 rounded-2xl focus:ring-4 focus:ring-pink-300 focus:border-pink-500 outline-none resize-none"></textarea>
                    <div class="mt-3 flex justify-end">
                        <button onclick="submitComment({{ post.id }})" class="px-8 py-3 bg-gradient-to-r from-pink-500 to-purple-600 text-white font-bold rounded-full hover:shadow-xl transition transform hover:scale-105">
                            <i class="fas fa-paper-plane mr-2"></i> Gửi bình luận
                        </button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Danh sách bình luận -->
        <div class="p-6">
            <h3 class="text-2xl font-bold text-gray-800 mb-6">Bình luận ({{ comments|length }})</h3>
            {% if comments %}
            <div class="space-y-6">
                {% for comment in comments %}
                <div class="flex gap-4 p-4 bg-gray-50 rounded-2xl hover:bg-gray-100 transition">
                    <!-- ✅ SỬA AVATAR TÁC GIẢ BÌNH LUẬN -->
                    <img src="{{ url_for('static', filename=comment.author.avatar or 'images/default-avatar.png') }}"
                        class="w-12 h-12 rounded-full ring-4 ring-white shadow">
                    <div class="flex-1">
                        <div class="flex items-center justify-between mb-2">
                            <h4 class="font-bold text-gray-900">{{ comment.author.name }}</h4>
                            <span class="text-sm text-gray-500">{{ comment.created_at.strftime('%H:%M %d/%m') }}</span>
                        </div>
                        <p class="text-gray-700 leading-relaxed">{{ comment.content | replace('\\n', '<br>') | safe }}</p>
                    </div>
                </div>
                {% endfor %}
            </div>
            {% else %}
            <div class="text-center py-12 text-gray-400">
                <i class="fas fa-comment-slash text-6xl mb-4"></i>
                <p class="text-lg">Chưa có bình luận nào</p>
                <p class="text-sm mt-2">Hãy là người đầu tiên bình luận nhé!</p>
            </div>
            {% endif %}
        </div>
    </div>

    <!-- Nút quay lại -->
    <div class="text-center mt-8">
        <a href="{{ url_for('home') }}" class="inline-flex items-center gap-2 text-pink-600 hover:text-pink-700 font-bold text-lg">
            <i class="fas fa-arrow-left"></i> Quay lại trang chủ
        </a>
    </div>
</div>

<!-- Toast thông báo -->
<div id="toast" class="hidden fixed top-20 right-4 bg-white border-l-4 border-green-500 shadow-xl rounded-lg p-4 z-50">
    <div class="flex items-center gap-3">
        <i class="fas fa-check-circle text-green-500 text-2xl"></i>
        <span id="toast-message" class="font-medium text-gray-800"></span>
    </div>
</div>

<script>
    function toggleMenu(postId) {
        document.querySelectorAll('[id^="menu-"]').forEach(m => {
            if (m.id !== `menu-${postId}`) m.classList.add('hidden');
        });
        document.getElementById(`menu-${postId}`).classList.toggle('hidden');
    }

    function likePost(postId) {
        fetch(`/like/${postId}`, { method: 'POST' })
            .then(r => r.json())
            .then(data => {
                location.reload();
            });
    }

    function focusCommentInput() {
        document.getElementById('comment-input').focus();
    }

    function submitComment(postId) {
        const content = document.getElementById('comment-input').value.trim();
        if (!content) return alert('Vui lòng nhập nội dung bình luận!');

        const formData = new FormData();
        formData.append('content', content);

        fetch(`/comment/${postId}`, {
            method: 'POST',
            body: formData
        })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    location.reload();
                } else {
                    alert('Lỗi: ' + data.error);
                }
            });
    }

    function reportPost(postId) {
        const reason = prompt('Lý do báo cáo bài viết:');
        if (!reason) return;

        const formData = new FormData();
        formData.append('reason', reason);

        fetch(`/report/${postId}`, {
            method: 'POST',
            body: formData
        })
            .then(r => r.json())
            .then(data => {
                alert(data.success ? 'Đã gửi báo cáo!' : data.error);
            });
    }

    function deletePost(postId) {
        if (!confirm('Bạn chắc chắn muốn xóa bài viết này?')) return;
        fetch(`/post/${postId}/delete`, { method: 'POST' })
            .then(() => location.href = '/');
    }

    function ratePost(postId, rating) {
        fetch(`/rate/${postId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ stars: rating })
        })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    showToast('Đã đánh giá bài viết!', true);
                } else {
                    showToast(data.error || 'Lỗi khi đánh giá', false);
                }
            });
    }

    function showToast(message, isSuccess = true) {
        const toast = document.getElementById('toast');
        const toastMessage = document.getElementById('toast-message');
        const icon = toast.querySelector('i');

        toastMessage.textContent = message;

        if (isSuccess) {
            toast.classList.remove('border-red-500');
            toast.classList.add('border-green-500');
            icon.classList.remove('fa-exclamation-circle', 'text-red-500');
            icon.classList.add('fa-check-circle', 'text-green-500');
        } else {
            toast.classList.remove('border-green-500');
            toast.classList.add('border-red-500');
            icon.classList.remove('fa-check-circle', 'text-green-500');
            icon.classList.add('fa-exclamation-circle', 'text-red-500');
        }

        toast.classList.remove('hidden');

        setTimeout(() => {
            toast.classList.add('hidden');
        }, 3000);
    }
</script>
{% endblock %}'''
    
    with open('post_detail_fixed.html', 'w', encoding='utf-8') as f:
        f.write(fixed_content)
    
    print("✅ Đã tạo file post_detail_fixed.html với tất cả avatar đã sửa")
    return True

if __name__ == "__main__":
    print("🚀 SỬA AVATAR TRONG POST_DETAIL.HTML")
    print("="*50)
    
    # Tạo file đã sửa
    success = create_post_detail_fixed()
    
    if success:
        print("\n🎉 HOÀN THÀNH!")
        print("📋 CÁC BƯỚC TIẾP THEO:")
        print("1. Sao chép nội dung file post_detail_fixed.html vào templates/post_detail.html")
        print("2. Kiểm tra route post_detail có truyền đúng dữ liệu không")
        print("3. Test lại hiển thị avatar trong trang chi tiết bài viết")
    else:
        print("\n❌ THẤT BẠI!")
        print("📝 Kiểm tra lại file post_detail.html")