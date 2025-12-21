# Script sửa lỗi hiển thị avatar sau khi cập nhật
# Vấn đề: Avatar mới không hiển thị ở trang home nhưng có ở header

import os
import re

def fix_avatar_display():
    """Sửa các vấn đề về hiển thị avatar"""
    
    print("🔧 SỬA LỖI HIỂN THỊ AVATAR")
    print("="*50)
    
    # 1. Kiểm tra và sửa profile.html
    if os.path.exists('templates/profile.html'):
        with open('templates/profile.html', 'r', encoding='utf-8') as f:
            profile_content = f.read()
        
        # Tìm và thay thế đường dẫn avatar
        old_avatar_pattern = r'src="/static/\{\{\s*user\.avatar\s*\}\}"'
        new_avatar_src = 'src="{{ url_for(\'static\', filename=user.avatar or \'images/default-avatar.png\') }}"'
        
        if re.search(old_avatar_pattern, profile_content):
            profile_content = re.sub(old_avatar_pattern, new_avatar_src, profile_content)
            
            with open('templates/profile.html', 'w', encoding='utf-8') as f:
                f.write(profile_content)
            
            print("✅ Đã sửa đường dẫn avatar trong profile.html")
        else:
            print("⚠️ Không tìm thấy đường dẫn avatar cần sửa trong profile.html")
    else:
        print("❌ Không tìm thấy file templates/profile.html")
    
    # 2. Thêm JavaScript chống cache vào profile.html
    if os.path.exists('templates/profile.html'):
        with open('templates/profile.html', 'r', encoding='utf-8') as f:
            profile_content = f.read()
        
        # Kiểm tra đã có script chống cache chưa
        if 'cache' not in profile_content.lower() or 'timestamp' not in profile_content.lower():
            # Thêm script trước thẻ </body> hoặc {% endblock %}
            script_tag = '''
<script>
document.getElementById('profileForm').addEventListener('submit', function() {
    // Xóa cache ảnh avatar sau khi cập nhật
    setTimeout(() => {
        const avatarImages = document.querySelectorAll('img[src*="avatar"]');
        avatarImages.forEach(img => {
            const src = img.src.split('?')[0];
            img.src = src + '?t=' + new Date().getTime();
        });
    }, 1000);
});
</script>
'''
            
            if '{% endblock %}' in profile_content:
                profile_content = profile_content.replace('{% endblock %}', script_tag + '\n{% endblock %}')
            elif '</body>' in profile_content:
                profile_content = profile_content.replace('</body>', script_tag + '\n</body>')
            else:
                profile_content += script_tag
            
            with open('templates/profile.html', 'w', encoding='utf-8') as f:
                f.write(profile_content)
            
            print("✅ Đã thêm script chống cache vào profile.html")
        else:
            print("⚠️ Đã có script chống cache trong profile.html")
    
    # 3. Kiểm tra route profile để đảm bảo xử lý avatar đúng
    if os.path.exists('app.py'):
        with open('app.py', 'r', encoding='utf-8') as f:
            app_content = f.read()
        
        # Kiểm tra route profile
        profile_route_pattern = r'@app\.route\(\'/profile\'[\s\S]*?def profile\(\):[\s\S]*?(?=@app\.route|\Z)'
        profile_match = re.search(profile_route_pattern, app_content)
        
        if profile_match:
            print("✅ Tìm thấy route profile")
            
            # Kiểm tra xử lý avatar
            if 'avatar' in profile_match.group(0):
                print("✅ Route profile có xử lý avatar")
            else:
                print("⚠️ Route profile có thể chưa xử lý avatar đúng cách")
        else:
            print("❌ Không tìm thấy route profile")
    
    # 4. Tạo hướng dẫn xóa cache trình duyệt
    cache_guide = '''
# HƯỚNG DẪN XÓA CACHE TRÌNH DUYỆT

## Chrome/Edge:
1. Nhấn Ctrl+Shift+Delete
2. Chọn "Cached images and files"
3. Nhấn "Clear data"

## Firefox:
1. Nhấn Ctrl+Shift+Delete
2. Chọn "Cache"
3. Nhấn "OK"

## Hoặc cách nhanh hơn:
1. Mửa trang profile
2. Nhấn Ctrl+F5 (hoặc Ctrl+Shift+R) để force reload
3. Hoặc mở Developer Tools (F12) -> Network tab -> Check "Disable cache"
'''
    
    with open('CACHE_CLEAR_GUIDE.md', 'w', encoding='utf-8') as f:
        f.write(cache_guide)
    
    print("✅ Đã tạo hướng dẫn xóa cache trong file CACHE_CLEAR_GUIDE.md")
    
    print("\n🎉 HOÀN THÀNH!")
    print("📋 Các bước tiếp theo:")
    print("1. Xóa cache trình duyệt (xem file CACHE_CLEAR_GUIDE.md)")
    print("2. Khởi động lại ứng dụng Flask")
    print("3. Test lại việc cập nhật avatar")
    print("4. Kiểm tra avatar hiển thị ở cả trang home và header")

if __name__ == "__main__":
    fix_avatar_display()