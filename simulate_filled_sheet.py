import sys
import os
import cv2
import json
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)
from omr_processor import OMRProcessor

def create_filled_sheet(processor, img, cccd_val, dethi_val, incorrect_questions, output_path):
    # Căn chỉnh phối cảnh về khổ chuẩn 1000x1414
    anchors = processor.find_anchors(img)
    if len(anchors) < 4:
        print(f"[!] Lỗi: Không tìm đủ 4 điểm định vị góc cho {output_path}")
        return False
        
    sorted_pts = processor.sort_anchors(anchors)
    TL, TR, BL, BR = sorted_pts
    src_pts = np.float32([TL, TR, BL, BR])
    dst_pts = np.float32([[50, 50], [950, 50], [50, 1364], [950, 1364]])
    M = cv2.getPerspectiveTransform(src_pts, dst_pts)
    warped = cv2.warpPerspective(img, M, (1000, 1414))
    
    # 1. Tô CCCD
    for col_idx, char in enumerate(cccd_val):
        digit = int(char)
        cx, cy = processor.coords["cccd"][col_idx][digit]
        cv2.circle(warped, (cx, cy), 6, (35, 35, 35), -1)
        
    # 2. Tô Đề thi số
    if "de_thi" in processor.coords:
        for col_idx, char in enumerate(dethi_val):
            digit = int(char)
            cx, cy = processor.coords["de_thi"][col_idx][digit]
            cv2.circle(warped, (cx, cy), 6, (35, 35, 35), -1)
            
    # 3. Đọc đáp án mẫu
    key_path = os.path.join(BASE_DIR, "data", "answer_key.json")
    with open(key_path, "r", encoding="utf-8") as f:
        answer_key = json.load(f)
        
    options_map = {"A": 0, "B": 1, "C": 2, "D": 3}
    alternate_options = {"A": "B", "B": "C", "C": "D", "D": "A"}
    
    for q_str, correct_ans in answer_key.items():
        q_num = int(q_str)
        ans_to_fill = correct_ans
        
        # Đổi đáp án nếu câu này muốn làm sai
        if q_num in incorrect_questions:
            ans_to_fill = alternate_options[correct_ans]
            
        opt_idx = options_map[ans_to_fill]
        cx, cy = processor.coords["answers"][q_str][opt_idx]
        cv2.circle(warped, (cx, cy), 6, (35, 35, 35), -1)
        
    cv2.imwrite(output_path, warped)
    print(f"[+] Đã tạo bài làm mẫu: {output_path} (CCCD: {cccd_val}, Đề: {dethi_val}, Số câu sai: {len(incorrect_questions)})")
    return True

def main():
    print("[*] Đang khởi tạo mô phỏng 5 phiếu trắc nghiệm đã tô...")
    
    coord_json_path = os.path.join(BASE_DIR, "data", "bubble_coordinates.json")
    processor = OMRProcessor(coord_json_path)
    
    png_path = os.path.join(BASE_DIR, "mau_thiet_ke_raw.png")
    pdf_path = os.path.join(BASE_DIR, "phieu_trac_nghiem.pdf")
    
    img = None
    if os.path.exists(png_path):
        img = cv2.imread(png_path)
        print(f"[+] Đọc ảnh nền thiết kế Photoshop: {png_path}")
    elif os.path.exists(pdf_path):
        images = processor.convert_pdf_to_images(pdf_path)
        page_num, img = images[0]
        print(f"[+] Đọc ảnh nền từ mẫu PDF: {pdf_path}")
    else:
        print("[!] Lỗi: Không tìm thấy mẫu PDF hay PNG nào.")
        return
        
    # Tạo 5 mẫu phiếu thi thử nghiệm khác nhau
    # Mẫu 1: Nguyễn Văn A (CCCD: 012345678901, Đề 1024, Sai 5 câu)
    create_filled_sheet(
        processor, img, 
        cccd_val="012345678901", 
        dethi_val="1024", 
        incorrect_questions=[5, 10, 15, 20, 25], 
        output_path=os.path.join(BASE_DIR, "phieu_mau_1.png")
    )
    
    # Mẫu 2: Trần Thị B (CCCD: 987654321098, Đề 2048, Sai 2 câu)
    create_filled_sheet(
        processor, img, 
        cccd_val="987654321098", 
        dethi_val="2048", 
        incorrect_questions=[9, 19], 
        output_path=os.path.join(BASE_DIR, "phieu_mau_2.png")
    )
    
    # Mẫu 3: Lê Văn C (CCCD: 111111111111, Đề 3126, Đúng 100% - 30/30 câu)
    create_filled_sheet(
        processor, img, 
        cccd_val="111111111111", 
        dethi_val="3126", 
        incorrect_questions=[], 
        output_path=os.path.join(BASE_DIR, "phieu_mau_3.png")
    )
    
    # Mẫu 4: Thí sinh tự do 1 (CCCD: 555555555555, Đề 9999, Sai 12 câu)
    create_filled_sheet(
        processor, img, 
        cccd_val="555555555555", 
        dethi_val="9999", 
        incorrect_questions=[2, 4, 6, 8, 12, 14, 16, 18, 22, 24, 26, 28], 
        output_path=os.path.join(BASE_DIR, "phieu_mau_4.png")
    )
    
    # Mẫu 5: Thí sinh tự do 2 (CCCD: 777777777777, Đề 8888, Sai 6 câu)
    create_filled_sheet(
        processor, img, 
        cccd_val="777777777777", 
        dethi_val="8888", 
        incorrect_questions=[1, 3, 11, 13, 21, 23], 
        output_path=os.path.join(BASE_DIR, "phieu_mau_5.png")
    )
    
    # Cũng ghi đè vào test_filled_sheet.png để phục vụ các script test tự động
    cv2.imwrite(os.path.join(BASE_DIR, "test_filled_sheet.png"), cv2.imread(os.path.join(BASE_DIR, "phieu_mau_1.png")))
    print("[+] Đã đồng bộ mẫu 1 vào test_filled_sheet.png")

if __name__ == "__main__":
    main()
