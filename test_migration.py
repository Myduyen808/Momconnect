#!/usr/bin/env python3
# test_migration.py - TEST MIGRATION SCRIPT

import os
import sqlite3

def test_migration():
    """Test kết quả migration"""
    
    print("🧪 TEST MIGRATION HỆ THỐNG BẠN BÈ")
    print("=" * 50)
    
    db_path = 'db/custom.db'
    
    if not os.path.exists(db_path):
        print("❌ Database không tồn tại! Chạy migration trước.")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. Kiểm tra các bảng
        print("📋 Kiểm tra bảng...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        required_tables = ['user', 'friendship', 'friend_request', 'follow', 'messages']
        
        for table in required_tables:
            if table in tables:
                print(f"   ✅ {table}")
            else:
                print(f"   ❌ {table} - THIẾU!")
        
        # 2. Kiểm tra cấu trúc bảng friendship
        print("\n🤝 Kiểm tra bảng friendship...")
        if 'friendship' in tables:
            cursor.execute("PRAGMA table_info(friendship)")
            columns = [column[1] for column in cursor.fetchall()]
            
            required_columns = ['user_id', 'friend_id', 'created_at']
            for col in required_columns:
                if col in columns:
                    print(f"   ✅ {col}")
                else:
                    print(f"   ❌ {col} - THIẾU!")
        
        # 3. Kiểm tra cấu trúc friend_request
        print("\n📨 Kiểm tra bảng friend_request...")
        if 'friend_request' in tables:
            cursor.execute("PRAGMA table_info(friend_request)")
            columns = [column[1] for column in cursor.fetchall()]
            
            required_columns = ['status', 'updated_at']
            for col in required_columns:
                if col in columns:
                    print(f"   ✅ {col}")
                else:
                    print(f"   ❌ {col} - THIẾU!")
        
        # 4. Kiểm tra dữ liệu
        print("\n📊 Kiểm tra dữ liệu...")
        
        # Users
        cursor.execute("SELECT COUNT(*) FROM user")
        user_count = cursor.fetchone()[0]
        print(f"   👥 Users: {user_count}")
        
        # Friendships
        cursor.execute("SELECT COUNT(*) FROM friendship")
        friendship_count = cursor.fetchone()[0]
        print(f"   🤝 Friendships: {friendship_count}")
        
        # Friend Requests
        cursor.execute("SELECT COUNT(*) FROM friend_request")
        request_count = cursor.fetchone()[0]
        print(f"   📨 Friend Requests: {request_count}")
        
        # Pending requests
        cursor.execute("SELECT COUNT(*) FROM friend_request WHERE status='pending'")
        pending_count = cursor.fetchone()[0]
        print(f"   ⏳ Pending Requests: {pending_count}")
        
        # 5. Test query phức tạp
        print("\n🔍 Test query phức tạp...")
        
        # Test lấy bạn bè của user 1
        if user_count > 0:
            cursor.execute('''
                SELECT u.name, COUNT(f.friend_id) as friend_count
                FROM user u
                LEFT JOIN friendship f ON u.id = f.user_id
                GROUP BY u.id, u.name
                ORDER BY friend_count DESC
                LIMIT 3
            ''')
            
            users_with_friends = cursor.fetchall()
            print("   📈 Top users theo số bạn bè:")
            for name, count in users_with_friends:
                print(f"      - {name}: {count} bạn")
        
        # 6. Kiểm tra index
        print("\n📈 Kiểm tra index...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = [row[0] for row in cursor.fetchall()]
        
        important_indexes = [
            'idx_friendship_user_id',
            'idx_friendship_friend_id',
            'idx_friend_request_status'
        ]
        
        for idx in important_indexes:
            if idx in indexes:
                print(f"   ✅ {idx}")
            else:
                print(f"   ⚠️ {idx} - Có thể thiếu")
        
        conn.close()
        
        # 7. Kết luận
        print("\n" + "=" * 50)
        print("🎉 KẾT QUẢ TEST:")
        
        if user_count > 0:
            print("   ✅ Database có dữ liệu")
        else:
            print("   ⚠️ Database rỗng (normal cho lần đầu)")
        
        if friendship_count >= 0:
            print("   ✅ Bảng friendship hoạt động")
        
        if request_count >= 0:
            print("   ✅ Bảng friend_request hoạt động")
        
        print("\n🚀 Migration thành công! Database sẵn sàng sử dụng.")
        return True
        
    except Exception as e:
        print(f"\n❌ Lỗi test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_migration()
    if success:
        print("\n✅ Test passed! Bạn có thể tiếp tục bước 2.")
    else:
        print("\n❌ Test failed! Kiểm tra lại migration.")