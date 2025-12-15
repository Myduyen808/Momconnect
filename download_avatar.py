# download_avatar.py
import requests
import os

# URL ảnh ổn định 100% từ GitHub (ảnh mẹ và bé)
url = "https://github.com/utahta/python-avatar/raw/master/examples/avatar.jpg"
save_path = "static/default.jpg"

os.makedirs("static", exist_ok=True)

print("Đang tải avatar mặc định từ GitHub...")
response = requests.get(url, timeout=10)

if response.status_code == 200:
    with open(save_path, 'wb') as f:
        f.write(response.content)
    print(f"Đã lưu: {save_path}")
else:
    print(f"Lỗi tải ảnh: {response.status_code}")
    print("Sẽ tạo ảnh giả bằng PIL...")

    # Tạo ảnh giả nếu lỗi mạng
    try:
        from PIL import Image, ImageDraw
        img = Image.new('RGB', (120, 120), (244, 114, 182))
        draw = ImageDraw.Draw(img)
        draw.ellipse((30, 20, 90, 80), fill=(255, 255, 255))
        draw.rectangle((40, 80, 80, 110), fill=(255, 255, 255))
        img.save(save_path)
        print("Đã tạo ảnh giả: static/default.jpg")
    except ImportError:
        print("Cần cài PIL: pip install pillow")