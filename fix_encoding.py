# fix_encoding.py - SCRIPT SỬA LỖI ENCODING

def fix_encoding():
    """Sửa lỗi encoding trong file app.py"""
    
    try:
        print("🔧 Đang sửa lỗi encoding trong app.py...")
        
        # Đọc file với encoding hiện tại
        with open('app.py', 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        
        # Sửa các lỗi encoding phổ biến
        content = content.replace('\u0110', 'Đ')
        content = content.replace('\u0111', 'ư')
        content = content.replace('\u0112', 'ờ')
        content = content.replace('\u0113', 'ơ')
        content = content.replace('\u0114', 'ở')
        content = content.replace('\u0115', 'ỡ')
        content = content.replace('\u0116', 'ợ')
        content = content.replace('\u0117', 'ợ')
        content = content.replace('\u0118', 'ợ')
        content = content.replace('\u0119', 'ợ')
        content = content.replace('\u011a', 'ợ')
        content = content.replace('\u011b', 'ợ')
        content = content.replace('\u011c', 'ợ')
        content = content.replace('\u011d', 'ợ')
        content = content.replace('\u011e', 'ợ')
        content = content.replace('\u011f', 'ợ')
        
        # Sửa các lỗi encoding khác
        content = content.replace('\u0122', 'ề')
        content = content.replace('\u0123', 'ề')
        content = content.replace('\u0124', 'ề')
        content = content.replace('\u0125', 'ề')
        content = content.replace('\u0126', 'ề')
        content = content.replace('\u0127', 'ề')
        content = content.replace('\u0128', 'ề')
        content = content.replace('\u0129', 'ề')
        content = content.replace('\u012a', 'ề')
        content = content.replace('\u012b', 'ề')
        
        # Backup file cũ
        with open('app_backup_encoding.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print("✅ Đã backup file app.py thành app_backup_encoding.py")
        
        # Ghi lại file đã sửa
        with open('app.py', 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ Đã sửa lỗi encoding trong app.py!")
        print("\n📝 Các bước tiếp theo:")
        print("1. Kiểm tra file app.py đã được sửa")
        print("2. Chạy lại: python app.py")
        print("3. Test các chức năng")
        
        return True
        
    except Exception as e:
        print(f"❌ Lỗi khi sửa encoding: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("🚀 Bắt đầu sửa lỗi encoding...")
    success = fix_encoding()
    
    if success:
        print("\n🎉 Hoàn tất! Hãy thử chạy lại ứng dụng.")
    else:
        print("\n❌ Vui lòng kiểm tra lỗi và thử lại.")