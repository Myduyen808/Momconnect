# Script sửa đường dẫn avatar trong profile.html
# Chỉ sửa 1 dòng duy nhất

import os
import re

def fix_profile_avatar():
    """Sửa đường dẫn avatar trong profile.html"""
    
    print("🔧 SỬA ĐƯỜNG DẪN AVATAR TRONG PROFILE.HTML")
    print("="*50)
    
    profile_file = 'templates/profile.html'
    
    if not os.path.exists(profile_file):
        print(f"❌ Không tìm thấy file {profile_file}")
        print("📝 Đảm bảo bạn đang ở thư mục chứa file templates/profile.html")
        return False
    
    # Đọc file
    with open(profile_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Tìm và thay thế đường dẫn avatar
    old_pattern = r'src="/static/\{\{\s*user\.avatar\s*\}\}"'
    new_src = 'src="{{ url_for(\'static\', filename=user.avatar or \'images/default-avatar.png\') }}"'
    
    if re.search(old_pattern, content):
        # Thay thế
        content = re.sub(old_pattern, new_src, content)
        
        # Ghi lại file
        with open(profile_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ Đã sửa đường dẫn avatar trong profile.html")
        print("📝 Đã thay thế:")
        print('   <img src="/static/{{ user.avatar }}"')
        print('   Thành:')
        print('   <img src="{{ url_for(\'static\', filename=user.avatar or \'images/default-avatar.png\') }}"')
        
        return True
    else:
        print("❌ Không tìm thấy đường dẫn avatar cần sửa")
        
        # Hiển thị các dòng có chứa avatar để debug
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            if 'avatar' in line.lower():
                print(f"   Dòng {i}: {line.strip()}")
        
        return False

def add_cache_script():
    """Thêm script chống cache vào profile.html"""
    
    print("\n🔧 THÊM SCRIPT CHỐNG CACHE")
    print("-"*30)
    
    profile_file = 'templates/profile.html'
    
    with open(profile_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Kiểm tra đã có script chưa
    if 'cache' in content.lower() and 'timestamp' in content.lower():
        print("✅ Đã có script chống cache")
        return True
    
    # Thêm script trước {% endblock %}
    cache_script = '''
<!-- Script chống cache avatar -->
<script>
document.getElementById('profileForm').addEventListener('submit', function() {
    setTimeout(() => {
        // Cập nhật tất cả avatar trên trang
        const avatarImages = document.querySelectorAll('img[src*="avatar"], img[src*="default-avatar"]');
        avatarImages.forEach(img => {
            const src = img.src.split('?')[0];
            img.src = src + '?t=' + new Date().getTime();
        });
        
        // Reload trang sau 1.5 giây
        setTimeout(() => {
            window.location.reload();
        }, 1500);
    }, 1000);
});
</script>
'''
    
    if '{% endblock %}' in content:
        content = content.replace('{% endblock %}', cache_script + '\n{% endblock %}')
        
        with open(profile_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ Đã thêm script chống cache vào profile.html")
        return True
    else:
        print("❌ Không tìm thấy {% endblock %} để thêm script")
        return False

if __name__ == "__main__":
    print("🚀 SỬA LỖI AVATAR PROFILE.HTML")
    print("="*50)
    
    # Sửa đường dẫn avatar
    avatar_fixed = fix_profile_avatar()
    
    # Thêm script chống cache
    cache_added = add_cache_script()
    
    print("\n🎉 KẾT QUẢ:")
    if avatar_fixed:
        print("✅ Đã sửa đường dẫn avatar")
    else:
        print("❌ Chưa sửa được đường dẫn avatar")
    
    if cache_added:
        print("✅ Đã thêm script chống cache")
    else:
        print("❌ Chưa thêm được script chống cache")
    
    print("\n📋 CÁC BƯỚC TIẾP THEO:")
    print("1. Khởi động lại ứng dụng Flask")
    print("2. Mở trang profile")
    print("3. Nhấn Ctrl+F5 để xóa cache")
    print("4. Cập nhật avatar mới")
    print("5. Kiểm tra avatar hiển thị ở trang home")
    
    if avatar_fixed and cache_added:
        print("\n🎯 Vấn đề của bạn đã được giải quyết!")
    else:
        print("\n⚠️ Có thể cần sửa thủ công nếu script không hoạt động")