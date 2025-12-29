// static/js/comments.js - HỆ THỐNG BÌNH LUẬN FACEBOOK-STYLE

// 🔥 STICKERS
const STICKERS = {
    'love': '❤️', 'laugh': '😂', 'wow': '😮', 'sad': '😢', 'angry': '😠',
    'like': '👍', 'fire': '🔥', 'clap': '👏', 'party': '🎉', 'thinking': '🤔'
};

// 🔥 HIỂN THỊ COMMENT VỚI REPLIES
function renderComment(comment, postId) {
    const isOwner = comment.user_id === {{ current_user.id if current_user.is_authenticated else 'null' }
};
const canDelete = isOwner || {{ 'true' if current_user.role == 'admin' else 'false' }};

return `
        <div class="comment-item" data-comment-id="${comment.id}">
            <div class="flex gap-3 p-4 bg-gray-50 rounded-2xl hover:bg-gray-100 transition">
                <img src="${comment.author.avatar || '/static/images/default-avatar.png'}" 
                    class="w-10 h-10 rounded-full object-cover ring-2 ring-white shadow-md flex-shrink-0">
                
                <div class="flex-1 min-w-0">
                    <!-- Tên + Nội dung -->
                    <div class="bg-white p-3 rounded-2xl shadow-sm">
                        <h4 class="font-bold text-gray-900 text-sm">${comment.author.name}</h4>
                        
                        ${comment.content ? `<p class="text-gray-700 text-sm mt-1 break-words">${linkifyAndHashtag(comment.content)}</p>` : ''}
                        
                        ${comment.sticker ? `<div class="text-6xl my-2">${comment.sticker}</div>` : ''}
                        
                        ${comment.image ? `<img src="${comment.image}" class="mt-2 rounded-xl max-w-xs cursor-pointer" onclick="openImageModal('${comment.image}')">` : ''}
                        
                        ${comment.video ? `<video controls class="mt-2 rounded-xl max-w-xs"><source src="${comment.video}" type="video/mp4"></video>` : ''}
                        
                        ${comment.is_edited ? '<span class="text-xs text-gray-400 ml-2">(đã chỉnh sửa)</span>' : ''}
                    </div>
                    
                    <!-- Hành động -->
                    <div class="flex items-center gap-4 mt-2 text-xs font-semibold text-gray-600">
                        <button onclick="likeComment(${comment.id})" class="hover:text-pink-600 transition">
                            <i class="fas fa-heart mr-1"></i>
                            <span id="comment-like-${comment.id}">${comment.likes_count || 0}</span>
                        </button>
                        
                        <button onclick="showReplyBox(${comment.id}, '${comment.author.name}')" class="hover:text-blue-600 transition">
                            <i class="fas fa-reply mr-1"></i> Trả lời
                        </button>
                        
                        ${isOwner ? `<button onclick="editComment(${comment.id})" class="hover:text-green-600"><i class="fas fa-edit"></i> Sửa</button>` : ''}
                        
                        ${canDelete ? `<button onclick="deleteComment(${comment.id})" class="hover:text-red-600"><i class="fas fa-trash"></i> Xóa</button>` : ''}
                        
                        <span class="text-gray-400">${comment.created_at}</span>
                    </div>
                    
                    <!-- Khung reply -->
                    <div id="reply-box-${comment.id}" class="hidden mt-3"></div>
                    
                    <!-- Replies -->
                    ${comment.replies && comment.replies.length > 0 ? `
                        <div class="ml-6 mt-3 space-y-2">
                            ${comment.replies.map(reply => renderComment(reply, postId)).join('')}
                        </div>
                    ` : ''}
                </div>
            </div>
        </div>
    `;
}

// 🔥 LINKIFY & HASHTAG
function linkifyAndHashtag(text) {
    // Hashtag
    text = text.replace(/#(\w+)/g, '<a href="/search?q=%23$1" class="text-blue-600 font-semibold hover:underline">#$1</a>');

    // Mention (@username)
    text = text.replace(/@(\w+)/g, '<span class="text-blue-600 font-semibold">@$1</span>');

    // URL
    text = text.replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank" class="text-blue-600 underline">$1</a>');

    return text;
}

// 🔥 GỬI BÌNH LUẬN MỚI
async function submitComment(postId, parentId = null) {
    const inputId = parentId ? `reply-input-${parentId}` : `comment-input-${postId}`;
    const input = document.getElementById(inputId);
    const content = input.value.trim();

    const fileInput = document.getElementById(parentId ? `reply-file-${parentId}` : `comment-file-${postId}`);
    const file = fileInput?.files[0];

    if (!content && !file) {
        showToast('Vui lòng nhập nội dung hoặc chọn ảnh/video!', false);
        return;
    }

    const formData = new FormData();
    if (content) formData.append('content', content);
    if (file) formData.append('media', file);
    if (parentId) formData.append('parent_id', parentId);

    try {
        const res = await fetch(`/comment/${postId}`, {
            method: 'POST',
            body: formData
        });

        const data = await res.json();

        if (data.success) {
            input.value = '';
            if (fileInput) fileInput.value = '';

            // Load lại comments
            await loadComments(postId);

            showToast('Đã gửi bình luận!', true);
        } else {
            showToast(data.error || 'Lỗi gửi bình luận', false);
        }
    } catch (error) {
        console.error('Error:', error);
        showToast('Lỗi kết nối', false);
    }
}

// 🔥 HIỂN THỊ Ô REPLY
function showReplyBox(commentId, authorName) {
    const container = document.getElementById(`reply-box-${commentId}`);
    if (!container) return;

    if (!container.classList.contains('hidden')) {
        container.classList.add('hidden');
        return;
    }

    container.innerHTML = `
        <div class="flex gap-3 bg-white p-3 rounded-xl shadow-sm border-2 border-blue-200">
            <img src="{{ url_for('static', filename=current_user.avatar or 'images/default-avatar.png') }}" 
                class="w-8 h-8 rounded-full ring-2 ring-blue-200">
            <div class="flex-1">
                <textarea id="reply-input-${commentId}" 
                    placeholder="Trả lời @${authorName}..." 
                    rows="2"
                    class="w-full px-3 py-2 border rounded-xl focus:ring-2 focus:ring-blue-300 outline-none text-sm"></textarea>
                <div class="flex items-center justify-between mt-2">
                    <div class="flex gap-2">
                        <label class="cursor-pointer text-gray-600 hover:text-blue-600">
                            <i class="fas fa-image"></i>
                            <input type="file" id="reply-file-${commentId}" accept="image/*,video/*" class="hidden">
                        </label>
                        <button onclick="showStickerPicker(${commentId}, true)" class="text-gray-600 hover:text-yellow-600">
                            <i class="fas fa-smile"></i>
                        </button>
                    </div>
                    <button onclick="submitComment({{ post.id }}, ${commentId})" 
                        class="px-4 py-2 bg-blue-600 text-white rounded-full text-sm font-bold hover:bg-blue-700">
                        Gửi
                    </button>
                </div>
            </div>
        </div>
    `;

    container.classList.remove('hidden');
    document.getElementById(`reply-input-${commentId}`).focus();
}

// 🔥 STICKER PICKER
function showStickerPicker(targetId, isReply = false) {
    const inputId = isReply ? `reply-input-${targetId}` : `comment-input-${targetId}`;
    const input = document.getElementById(inputId);

    const picker = document.createElement('div');
    picker.className = 'absolute bottom-full mb-2 left-0 bg-white p-3 rounded-xl shadow-2xl border-2 border-gray-200 grid grid-cols-5 gap-2 z-50';
    picker.innerHTML = Object.entries(STICKERS).map(([key, emoji]) =>
        `<button onclick="insertSticker('${inputId}', '${emoji}')" class="text-3xl hover:scale-125 transition">${emoji}</button>`
    ).join('');

    input.parentElement.style.position = 'relative';
    input.parentElement.appendChild(picker);

    setTimeout(() => picker.remove(), 5000);
}

function insertSticker(inputId, emoji) {
    const input = document.getElementById(inputId);
    input.value += emoji;
    input.focus();
}

// 🔥 SỬA BÌNH LUẬN
async function editComment(commentId) {
    const commentEl = document.querySelector(`[data-comment-id="${commentId}"]`);
    const contentEl = commentEl.querySelector('p');
    const oldContent = contentEl.textContent;

    const newContent = prompt('Sửa bình luận:', oldContent);
    if (!newContent || newContent === oldContent) return;

    try {
        const res = await fetch(`/comment/${commentId}/edit`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content: newContent })
        });

        const data = await res.json();

        if (data.success) {
            contentEl.innerHTML = linkifyAndHashtag(newContent);
            showToast('Đã cập nhật bình luận!', true);
        } else {
            showToast(data.error || 'Lỗi', false);
        }
    } catch (error) {
        showToast('Lỗi kết nối', false);
    }
}

// 🔥 XÓA BÌNH LUẬN
async function deleteComment(commentId) {
    if (!confirm('Xóa bình luận này?')) return;

    try {
        const res = await fetch(`/comment/${commentId}/delete`, { method: 'POST' });
        const data = await res.json();

        if (data.success) {
            document.querySelector(`[data-comment-id="${commentId}"]`).remove();
            showToast('Đã xóa bình luận!', true);
        } else {
            showToast(data.error || 'Lỗi', false);
        }
    } catch (error) {
        showToast('Lỗi kết nối', false);
    }
}

// 🔥 LIKE COMMENT
async function likeComment(commentId) {
    try {
        const res = await fetch(`/comment/${commentId}/like`, { method: 'POST' });
        const data = await res.json();

        if (data.success) {
            document.getElementById(`comment-like-${commentId}`).textContent = data.likes_count;
        }
    } catch (error) {
        console.error('Error:', error);
    }
}

// 🔥 LOAD COMMENTS
async function loadComments(postId) {
    try {
        const res = await fetch(`/api/comments/${postId}`);
        const comments = await res.json();

        const container = document.getElementById(`comments-list-${postId}`);
        container.innerHTML = comments.map(c => renderComment(c, postId)).join('');
    } catch (error) {
        console.error('Error loading comments:', error);
    }
}