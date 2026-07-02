import os
import json
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# 1. Cấu hình Font chữ hỗ trợ tiếng Việt trên macOS
font_pair_paths = [
    ("/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
    ("/Library/Fonts/Arial.ttf", "/Library/Fonts/Arial Bold.ttf"),
]
FONT_NAME = 'Helvetica'
FONT_BOLD_NAME = 'Helvetica-Bold'
font_loaded = False

for regular_path, bold_path in font_pair_paths:
    if os.path.exists(regular_path) and os.path.exists(bold_path):
        try:
            pdfmetrics.registerFont(TTFont('Arial', regular_path))
            pdfmetrics.registerFont(TTFont('Arial-Bold', bold_path))
            FONT_NAME = 'Arial'
            FONT_BOLD_NAME = 'Arial-Bold'
            font_loaded = True
            break
        except Exception:
            pass

# 2. Định nghĩa kích thước trang A4 và lề
W, H = A4  # 595.27 x 841.89
M = 30     # Lề (Margin)
S = 20     # Kích thước điểm định vị (Anchor Size)

# 3. Hàm chuyển đổi tọa độ từ PDF sang Ảnh phẳng 1000x1414
def to_image_coords(x, y):
    xi = 50 + (x - 40) / 515.27 * 900
    yi = 50 + (801.89 - y) / 761.89 * 1314
    return int(round(xi)), int(round(yi))

def draw_anchor(c, x, y):
    """Vẽ điểm định vị hình vuông màu đen đặc"""
    c.setFillColorRGB(0, 0, 0)
    c.rect(x, y, S, S, fill=True, stroke=False)

def draw_bubble(c, x, y, text, radius=4.5):
    """Vẽ một ô tròn trắc nghiệm nhỏ gọn và chữ bên trong"""
    c.setStrokeColorRGB(0.2, 0.2, 0.2)
    c.setLineWidth(0.4)
    c.setFillColorRGB(1, 1, 1)
    c.circle(x, y, radius, fill=True, stroke=True)
    
    # Sử dụng font Bold cho tất cả chữ số/chữ cái bên trong ô tròn để cực kỳ dễ đọc
    c.setFont(FONT_BOLD_NAME, radius * 1.15)
    c.setFillColorRGB(0.1, 0.1, 0.1)
    c.drawCentredString(x, y - radius * 0.35, text)

def generate_pdf(output_pdf_path, output_json_path):
    c = canvas.Canvas(output_pdf_path, pagesize=A4)
    
    # Lưu tọa độ để xử lý OMR (giữ nguyên để tránh hỏng tọa độ hiệu chỉnh)
    bubble_coords = {
        "cccd": [],      
        "de_thi": [],    
        "answers": {}    
    }
    
    # 4. Vẽ 4 điểm định vị ở 4 góc
    draw_anchor(c, M, H - M - S)  # TL
    draw_anchor(c, W - M - S, H - M - S)  # TR
    draw_anchor(c, M, M)  # BL
    draw_anchor(c, W - M - S, M)  # BR
    
    # 5. Phần tiêu đề (Top-Left) - Bỏ tiếng Anh, đổi thành tiêu đề chung viết tay môn thi
    c.setFont(FONT_BOLD_NAME, 15)
    c.setFillColorRGB(0, 0, 0)
    title_text = "PHIẾU TRẢ LỜI TRẮC NGHIỆM" if font_loaded else "PHIEU TRA LOI TRAC NGHIEM"
    c.drawString(40, 762, title_text)
    
    # 6. Hướng dẫn tô nhỏ gọn (Không vẽ phần thông tin cá nhân như Họ tên, Năm sinh, Chữ ký...)
    c.setFont(FONT_BOLD_NAME, 7)
    c.drawString(40, 532, "HƯỚNG DẪN TÔ:" if font_loaded else "HUONG DAN TO:")
    c.setFont(FONT_NAME, 6.5)
    c.drawString(110, 532, "- Tô đen kín vòng tròn chọn. Không gạch chéo." if font_loaded else "- To den kin vong tron chon. Khong gach cheo.")

    # 7. Phần tô SỐ CCCD (Giữa)
    c.setFont(FONT_BOLD_NAME, 8.5)
    c.drawCentredString(352, 747, "SỐ CCCD (12 SỐ)" if font_loaded else "SO CCCD (12 SO)")
    
    start_x_cccd = 260
    col_spacing = 15.2
    row_spacing = 16
    cccd_bubble_r = 5.2  # Tăng lên 5.2 (bằng với đáp án) để dễ nhìn
    
    for col in range(12):
        bubble_coords["cccd"].append([])
        cx = start_x_cccd + col * col_spacing
        
        # Hộp viết tay số CCCD ở đầu cột - nới rộng nhẹ cho cân đối
        c.setStrokeColorRGB(0.2, 0.2, 0.2)
        c.setLineWidth(0.6)
        c.setFillColorRGB(1, 1, 1)
        c.rect(cx - 7.0, 725, 14, 15, fill=True, stroke=True)
        
        # Vẽ các bong bóng 0-9
        for row in range(10):
            cy = 708 - row * row_spacing
            draw_bubble(c, cx, cy, str(row), radius=cccd_bubble_r)
            img_x, img_y = to_image_coords(cx, cy)
            bubble_coords["cccd"][col].append([img_x, img_y])

    # 8. Phần tô Đề thi số (Phải)
    c.setFont(FONT_BOLD_NAME, 8.5)
    c.drawCentredString(508, 747, "ĐỀ THI SỐ" if font_loaded else "DE THI SO")
    
    start_x_dethi = 485
    for col in range(4):
        bubble_coords["de_thi"].append([])
        cx = start_x_dethi + col * col_spacing
        
        # Hộp viết tay Mã đề ở đầu cột - nới rộng nhẹ cho cân đối
        c.setStrokeColorRGB(0.2, 0.2, 0.2)
        c.setLineWidth(0.6)
        c.setFillColorRGB(1, 1, 1)
        c.rect(cx - 7.0, 725, 14, 15, fill=True, stroke=True)
        
        # Vẽ các bong bóng 0-9
        for row in range(10):
            cy = 708 - row * row_spacing
            draw_bubble(c, cx, cy, str(row), radius=cccd_bubble_r)
            img_x, img_y = to_image_coords(cx, cy)
            bubble_coords["de_thi"][col].append([img_x, img_y])

    # 9. Bảng đáp án chia làm 3 cột (Mỗi cột 10 câu)
    c.setFont(FONT_BOLD_NAME, 11)
    c.drawCentredString(W / 2.0, 508, "BẢNG ĐÁP ÁN" if font_loaded else "BANG DAP AN")
    
    # Định nghĩa 3 hộp bao quanh 3 cột đáp án
    box_w = 155
    box_h = 280
    box_y = 200
    
    box1_l = 40
    box2_l = 220
    box3_l = 400
    
    ans_spacing_y = 24
    ans_bubble_r = 5.2
    
    def draw_answer_column(start_x, q_start, box_left):
        # Vẽ tiêu đề cột A B C D bên trong hộp
        c.setFont(FONT_BOLD_NAME, 8)
        c.setFillColorRGB(0.3, 0.3, 0.3)
        c.drawCentredString(start_x + 32, box_y + box_h - 18, "A")
        c.drawCentredString(start_x + 54, box_y + box_h - 18, "B")
        c.drawCentredString(start_x + 76, box_y + box_h - 18, "C")
        c.drawCentredString(start_x + 98, box_y + box_h - 18, "D")
        c.setLineWidth(0.4)
        c.line(box_left + 10, box_y + box_h - 24, box_left + box_w - 10, box_y + box_h - 24)
        
        # Vẽ 10 câu hỏi
        for idx in range(10):
            q_num = q_start + idx
            qy = (box_y + box_h - 45) - idx * ans_spacing_y
            
            # Vẽ số thứ tự câu hỏi
            c.setFont(FONT_BOLD_NAME, 9)
            c.setFillColorRGB(0, 0, 0)
            c.drawString(start_x, qy - 3, f"{q_num:02d}:")
            
            # Vẽ các bong bóng A, B, C, D
            options = ["A", "B", "C", "D"]
            q_coords = []
            for o_idx, opt in enumerate(options):
                ox = start_x + 32 + o_idx * 22
                draw_bubble(c, ox, qy, opt, radius=ans_bubble_r)
                img_x, img_y = to_image_coords(ox, qy)
                q_coords.append([img_x, img_y])
                
            bubble_coords["answers"][str(q_num)] = q_coords
            
            # Vẽ dòng kẻ ngang mờ giữa các câu hỏi
            c.setStrokeColorRGB(0.9, 0.9, 0.9)
            c.setLineWidth(0.2)
            c.line(box_left + 10, qy - 12, box_left + box_w - 10, qy - 12)
            
    # Vẽ viền bao quanh 3 cột
    c.setStrokeColorRGB(0.4, 0.4, 0.4)
    c.setLineWidth(0.8)
    c.rect(box1_l, box_y, box_w, box_h, fill=False, stroke=True)
    c.rect(box2_l, box_y, box_w, box_h, fill=False, stroke=True)
    c.rect(box3_l, box_y, box_w, box_h, fill=False, stroke=True)
    
    # Chạy vẽ nội dung đáp án bên trong 3 hộp
    draw_answer_column(box1_l + 12, 1, box1_l)
    draw_answer_column(box2_l + 12, 11, box2_l)
    draw_answer_column(box3_l + 12, 21, box3_l)

    c.showPage()
    c.save()
    
    # Lưu file JSON tọa độ
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(bubble_coords, f, indent=4)
    print(f"[+] PDF template generated: {output_pdf_path}")
    print(f"[+] Coordinates JSON generated: {output_json_path}")

if __name__ == "__main__":
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)
    generate_pdf(
        os.path.join(BASE_DIR, "phieu_trac_nghiem.pdf"),
        os.path.join(BASE_DIR, "data", "bubble_coordinates.json")
    )
    
    # 10. Tự động chuyển đổi PDF sang tệp hình ảnh PNG thô chất lượng cao (300 DPI) để sửa Photoshop
    try:
        import fitz
        pdf_path = os.path.join(BASE_DIR, "phieu_trac_nghiem.pdf")
        png_path = os.path.join(BASE_DIR, "mau_thiet_ke_raw.png")
        doc = fitz.open(pdf_path)
        page = doc[0]
        pix = page.get_pixmap(dpi=300, alpha=False)
        pix.save(png_path)
        print(f"[+] Clean PNG template for Photoshop generated: {png_path}")
    except Exception as e:
        print(f"[!] Error generating PNG template: {str(e)}")
