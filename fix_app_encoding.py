# fix_app_encoding.py - SCRIPT SỬA TOÀN DIỆN FILE APP.PY

import os
import re

def fix_app_encoding():
    """Sửa lỗi encoding trong file app.py"""
    
    print("🔧 Đang sửa lỗi encoding trong app.py...")
    
    try:
        # Đọc file app.py
        with open('app.py', 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        
        print("✅ Đã đọc file app.py thành công")
        
        # Tìm tất cả các lỗi encoding Unicode phổ biến
        unicode_errors = [
            r'\\u0110',  # Đ
            r'\\u0111',  # ư
            r'\\u0112',  # ờ
            r'\\u0113',  # ơ
            r'\\u0114',  # ở
            r'\\u0115',  # ở
            r'\\u0116',  # ở
            r'\\u0117',  # ợ
            r'\\u0118',  # ợ
            r'\\u0119',  # ợ
            r'\\u011a',  # ợ
            r'\\u011b',  # ợ
            r'\\u011c',  # ợ
            r'\\u011d',  # ợ
            r'\\u011e',  # ợ
            r'\\u011f',  # ợ
            r'\\u0122',  # ề
            r'\\u0123',  # ề
            r'\\u0124',  # ề
            r'\\u0125',  # ề
            r'\\u0126',  # ề
            r'\\u0127',  # ề
            r'\\u0128',  # ề
            r'\\u0129',  # ề
            r'\\u012a',  # ề
            r'\\u012b',  # ề
        ]
        
        # Thay thế tất cả các lỗi encoding
        fixed_content = content
        for error in unicode_errors:
            fixed_content = fixed_content.replace(error, 'Đ')
        
        print(f"✅ Đã sửa {len(unicode_errors)} lỗi encoding Unicode")
        
        # Backup file cũ
        with open('app_backup_unicode.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print("✅ Đã backup file app.py thành app_backup_unicode.py")
        
        # Ghi lại file đã sửa
        with open('app.py', 'w', encoding='utf-8') as f:
            f.write(fixed_content)
        
        print("✅ Đã sửa và ghi lại file app.py!")
        
        # Kiểm tra lại
        with open('app.py', 'r', encoding='utf-8') as f:
            fixed_content = f.read()
        
        # Kiểm tra còn lỗi không
        remaining_errors = []
        for error in unicode_errors:
            if error in fixed_content:
                remaining_errors.append(error)
        
        if remaining_errors:
            print(f"⚠️ Còn {len(remaining_errors)} lỗi chưa được sửa: {remaining_errors}")
        else:
            print("✅ Tất cả lỗi encoding đã được sửa!")
        
        return True
        
    except Exception as e:
        print(f"❌ Lỗi khi sửa encoding: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("🚀 Bắt đầu sửa lỗi encoding trong app.py...")
    success = fix_app_encoding()
    
    if success:
        print("\n🎉 Hoàn tất!")
        print("\n📝 Các bước tiếp theo:")
        print("1. Kiểm tra file app.py đã được sửa")
        print("2. Chạy lại ứng dụng: python app.py")
        print("3. Test các chức năng kết bạn")
        print("\n✅ Lưu ý: Nếu vẫn còn lỗi, hãy mở file app.py trong Notepad++ và kiểm tra encoding")
    else:
        print("\n❌ Vui lòng kiểm tra lỗi và thử lại")