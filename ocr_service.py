# ocr_service.py
import pytesseract
from PIL import Image
import re
from datetime import datetime

class CertificateOCR:
    def __init__(self):
        # Đường dẫn Tesseract (Windows)
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        pass
    
    def extract_text(self, image_path):
        """Đọc text từ ảnh"""
        try:
            img = Image.open(image_path)
            # Đọc text (hỗ trợ tiếng Việt)
            text = pytesseract.image_to_string(img, lang='vie+eng')
            return text
        except Exception as e:
            print(f"Lỗi OCR: {e}")
            return None
    
    def parse_certificate(self, text):
        """Parse thông tin từ text"""
        info = {
            'name': None,
            'cert_number': None,
            'specialty': None,
            'issue_org': None,
            'issue_date': None,
            'expiry_date': None
        }
        
        if not text:
            return info
        
        # 1. TÌM TÊN (sau "Chứng nhận" hoặc các từ khóa)
        name_patterns = [
            r'(?:Chứng nhận|Certificate)\s*(?:rằng|that)?\s*\n\s*([A-ZÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ\s\.]+)',
            r'(?:Họ và tên|Name):\s*([A-ZÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ\s\.]+)',
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                info['name'] = match.group(1).strip()
                break
        
        # 2. TÌM SỐ CHỨNG CHỈ
        cert_patterns = [
            r'(?:Số chứng chỉ|Certificate No|Số):\s*([A-Z0-9\-/]+)',
            r'\b([A-Z]{2,}-[A-Z]{3,}-\d{4}-\d+)\b',  # VN-NUT-2024-001258
        ]
        
        for pattern in cert_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                info['cert_number'] = match.group(1).strip()
                break
        
        # 3. TÌM CHUYÊN MÔN
        specialty_patterns = [
            r'(?:Chuyên gia|Expert)\s+([A-ZÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ\s]+?)(?:\n|Số)',
            r'(?:Lĩnh vực|Field):\s*([^\n]+)',
        ]
        
        for pattern in specialty_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                info['specialty'] = match.group(1).strip()
                break
        
        # 4. TÌM CƠ QUAN CẤP
        org_patterns = [
            r'(?:Cơ quan cấp|Issued by|Issued By):\s*([^\n]+)',
            r'(National[^\n]+)',  # ✅ THÊM: cho "National University"
            r'(Ministry[^\n]+)',  # ✅ THÊM: cho "Ministry of ..."
            r'(Department[^\n]+)',
        ]
        
        for pattern in org_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                info['issue_org'] = match.group(1).strip()
                break
        
        # 5. TÌM NGÀY CẤP
        date_patterns = [
            r'(?:Ngày cấp|Issue date):\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})',
            r'(\d{1,2})\s*(?:tháng|\/)\s*(\d{1,2})\s*(?:năm|\/)\s*(\d{4})',
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    if len(match.groups()) == 1:
                        # Format: 15/03/2024
                        date_str = match.group(1)
                        info['issue_date'] = datetime.strptime(date_str, '%d/%m/%Y').strftime('%Y-%m-%d')
                    else:
                        # Format: 15 tháng 03 năm 2024
                        day, month, year = match.groups()
                        info['issue_date'] = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                    break
                except:
                    pass
        
        # 6. TÌM NGÀY HẾT HẠN
        expiry_patterns = [
                r'(?:Hiệu lực|Valid until|Expiry|Expires):\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})',
                r'(?:Valid|Validity):\s*\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4}\s*(?:to|-)\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})',
            ]
        
        for pattern in expiry_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    date_str = match.group(1)
                    info['expiry_date'] = datetime.strptime(date_str, '%d/%m/%Y').strftime('%Y-%m-%d')
                    break
                except:
                    pass
        
        return info

# Khởi tạo
ocr_service = CertificateOCR()