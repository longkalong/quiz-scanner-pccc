import cv2
import numpy as np
import json
import os
import fitz  # PyMuPDF

class OMRProcessor:
    def __init__(self, coord_json_path):
        # Load bubble coordinates from JSON
        with open(coord_json_path, "r", encoding="utf-8") as f:
            self.coords = json.load(f)
            
    def convert_pdf_to_images(self, pdf_path):
        """Chuyển đổi từng trang PDF thành danh sách ảnh numpy (BGR)"""
        images = []
        doc = fitz.open(pdf_path)
        for page_num in range(len(doc)):
            page = doc[page_num]
            # Tăng độ phân giải lên 300 DPI để nhận diện chính xác
            pix = page.get_pixmap(dpi=300)
            img_data = pix.tobytes("png")
            nparr = np.frombuffer(img_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            images.append((page_num + 1, img))
        return images

    def find_anchors(self, img):
        """Tìm 4 điểm định vị màu đen ở 4 góc của phiếu trắc nghiệm"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Khử nhiễu nhẹ
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        # Nhị phân hóa thích ứng nghịch đảo (nền đen, vật thể trắng)
        thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
        
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        squares = []
        h, w = img.shape[:2]
        min_area = (w * h) * 0.00015  # Tối thiểu 0.015% diện tích ảnh
        max_area = (w * h) * 0.03     # Tối đa 3% diện tích ảnh
        
        for c in contours:
            area = cv2.contourArea(c)
            if min_area < area < max_area:
                peri = cv2.arcLength(c, True)
                approx = cv2.approxPolyDP(c, 0.04 * peri, True)
                # Kiểm tra xem có phải hình tứ giác không
                if len(approx) == 4:
                    (x, y, cw, cb) = cv2.boundingRect(approx)
                    aspect_ratio = cw / float(cb)
                    # Kiểm tra độ vuông góc (tỷ lệ cạnh gần 1:1)
                    if 0.8 <= aspect_ratio <= 1.25:
                        # Kiểm tra độ đặc: hình vuông gốc màu đen phải được tô đầy
                        mask = np.zeros(thresh.shape, dtype="uint8")
                        cv2.drawContours(mask, [approx], -1, 255, -1)
                        mean_val = cv2.mean(thresh, mask=mask)[0]
                        if mean_val > 180:  # Trên 70% số pixel là trắng trong thresh nghịch đảo
                            M = cv2.moments(c)
                            if M["m00"] != 0:
                                cX = int(M["m10"] / M["m00"])
                                cY = int(M["m01"] / M["m00"])
                                squares.append((cX, cY))
        return squares

    def sort_anchors(self, pts):
        """Sắp xếp 4 điểm định vị theo thứ tự: TL (trên-trái), TR (trên-phải), BL (dưới-trái), BR (dưới-phải)"""
        # Sắp xếp theo trục X trước
        pts = sorted(pts, key=lambda p: p[0])
        leftmost = pts[:2]
        rightmost = pts[2:]
        
        # Sắp xếp nhóm bên trái theo Y để tìm TL và BL
        TL = min(leftmost, key=lambda p: p[1])
        BL = max(leftmost, key=lambda p: p[1])
        
        # Sắp xếp nhóm bên phải theo Y để tìm TR và BR
        TR = min(rightmost, key=lambda p: p[1])
        BR = max(rightmost, key=lambda p: p[1])
        
        return [TL, TR, BL, BR]

    def process_sheet(self, img):
        """
        Xử lý OMR trên một ảnh phiếu quét.
        Trả về: (dict_ket_qua, error_message, debug_img_base64)
        """
        # 1. Tìm điểm định vị
        anchors = self.find_anchors(img)
        if len(anchors) < 4:
            return None, f"Lỗi: Không tìm đủ 4 điểm định vị góc (Tìm thấy {len(anchors)} điểm). Vui lòng quét thẳng hoặc kiểm tra lại chất lượng ảnh.", None
            
        if len(anchors) > 4:
            # Chọn ra 4 điểm tốt nhất bằng cách tính khoảng cách giữa chúng gần với tỷ lệ A4 nhất
            # Hoặc chọn 4 điểm nằm xa nhau nhất ở các góc
            # Đơn giản: Sắp xếp theo các góc xa nhất của ảnh
            h, w = img.shape[:2]
            corners = [(0, 0), (w, 0), (0, h), (w, h)]
            best_4 = []
            for corner in corners:
                # Tìm điểm gần góc nhất
                closest_pt = min(anchors, key=lambda p: np.linalg.norm(np.array(p) - np.array(corner)))
                best_4.append(closest_pt)
            # Loại bỏ trùng lặp nếu có
            anchors = list(set(best_4))
            if len(anchors) < 4:
                return None, "Lỗi: Không xác định được 4 góc chuẩn xác do ảnh bị nhiễu nhiều hình vuông.", None

        # Sắp xếp các điểm định vị
        sorted_pts = self.sort_anchors(anchors)
        TL, TR, BL, BR = sorted_pts
        
        # 2. Thực hiện căn chỉnh phối cảnh (Perspective Warp) về khổ chuẩn 1000x1414
        src_pts = np.float32([TL, TR, BL, BR])
        dst_pts = np.float32([[50, 50], [950, 50], [50, 1364], [950, 1364]])
        
        M = cv2.getPerspectiveTransform(src_pts, dst_pts)
        warped = cv2.warpPerspective(img, M, (1000, 1414))
        
        # 3. Tiền xử lý ảnh đã căn chỉnh để dò bong bóng
        gray_warped = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
        # Sử dụng Adaptive Threshold để khử bóng mờ do ánh sáng không đều khi chụp/quét
        thresh_warped = cv2.adaptiveThreshold(
            gray_warped, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 51, 15
        )
        
        # Tạo ảnh debug vẽ các vòng tròn lên để hiển thị cho người dùng xem
        debug_img = warped.copy()
        
        # 4. Nhận diện số CCCD (12 chữ số)
        cccd_result = []
        for col_idx, col_coords in enumerate(self.coords["cccd"]):
            col_ratios = []
            for digit, (cx, cy) in enumerate(col_coords):
                # Tạo mask hình tròn tại vị trí bong bóng
                mask = np.zeros(thresh_warped.shape, dtype="uint8")
                cv2.circle(mask, (cx, cy), 6, 255, -1)  # Bán kính 6 pixel trong ảnh 1000x1414
                
                # Tính lượng pixel trắng được tô trong mask
                total_pixels = np.sum(mask == 255)
                filled_pixels = cv2.countNonZero(cv2.bitwise_and(thresh_warped, mask))
                ratio = filled_pixels / float(total_pixels)
                col_ratios.append(ratio)
                
            # Phân tích tỷ lệ tô của cột CCCD
            max_ratio_idx = np.argmax(col_ratios)
            max_ratio = col_ratios[max_ratio_idx]
            
            # Sắp xếp các tỷ lệ tô để so sánh độ chênh lệch
            sorted_ratios = sorted(col_ratios, reverse=True)
            
            # Kiểm tra xem có được tô không
            if max_ratio > 0.35: # Ngưỡng tối thiểu được tô
                # Nếu có sự chênh lệch rõ ràng với số lớn thứ hai (tránh nhiễu hoặc tô trùng)
                if len(sorted_ratios) > 1 and (max_ratio - sorted_ratios[1] > 0.20):
                    cccd_result.append(str(max_ratio_idx))
                    # Vẽ màu xanh lá cho ô được chọn trên ảnh debug
                    cv2.circle(debug_img, tuple(col_coords[max_ratio_idx]), 6, (0, 255, 0), 2)
                else:
                    cccd_result.append("?") # Lỗi tô trùng hoặc không rõ ràng
                    # Vẽ màu đỏ cảnh báo tô trùng
                    for r_idx, r_val in enumerate(col_ratios):
                        if r_val > 0.35:
                            cv2.circle(debug_img, tuple(col_coords[r_idx]), 6, (0, 0, 255), 2)
            else:
                cccd_result.append("?") # Không tô
                
        cccd_str = "".join(cccd_result)
        
        # 4.2 Nhận diện số Đề thi (4 chữ số)
        dethi_result = []
        if "de_thi" in self.coords:
            for col_idx, col_coords in enumerate(self.coords["de_thi"]):
                col_ratios = []
                for digit, (cx, cy) in enumerate(col_coords):
                    mask = np.zeros(thresh_warped.shape, dtype="uint8")
                    cv2.circle(mask, (cx, cy), 6, 255, -1)
                    total_pixels = np.sum(mask == 255)
                    filled_pixels = cv2.countNonZero(cv2.bitwise_and(thresh_warped, mask))
                    ratio = filled_pixels / float(total_pixels)
                    col_ratios.append(ratio)
                    
                max_ratio_idx = np.argmax(col_ratios)
                max_ratio = col_ratios[max_ratio_idx]
                sorted_ratios = sorted(col_ratios, reverse=True)
                
                if max_ratio > 0.35:
                    if len(sorted_ratios) > 1 and (max_ratio - sorted_ratios[1] > 0.20):
                        dethi_result.append(str(max_ratio_idx))
                        cv2.circle(debug_img, tuple(col_coords[max_ratio_idx]), 6, (0, 255, 0), 2)
                    else:
                        dethi_result.append("?")
                        for r_idx, r_val in enumerate(col_ratios):
                            if r_val > 0.35:
                                cv2.circle(debug_img, tuple(col_coords[r_idx]), 6, (0, 0, 255), 2)
                else:
                    dethi_result.append("?")
        else:
            dethi_result = ["0", "0", "0", "0"]
            
        dethi_str = "".join(dethi_result)
        
        # 5. Nhận diện các câu trả lời trắc nghiệm (30 câu)
        answers_result = {}
        for q_num, q_coords in self.coords["answers"].items():
            q_ratios = []
            options = ["A", "B", "C", "D"]
            for o_idx, (cx, cy) in enumerate(q_coords):
                # Tạo mask
                mask = np.zeros(thresh_warped.shape, dtype="uint8")
                cv2.circle(mask, (cx, cy), 6, 255, -1)
                
                total_pixels = np.sum(mask == 255)
                filled_pixels = cv2.countNonZero(cv2.bitwise_and(thresh_warped, mask))
                ratio = filled_pixels / float(total_pixels)
                q_ratios.append(ratio)
                
            max_ratio_idx = np.argmax(q_ratios)
            max_ratio = q_ratios[max_ratio_idx]
            sorted_ratios = sorted(q_ratios, reverse=True)
            
            # Phán quyết đáp án
            if max_ratio > 0.35:
                # Kiểm tra tô trùng
                if len(sorted_ratios) > 1 and (max_ratio - sorted_ratios[1] > 0.20):
                    chosen_opt = options[max_ratio_idx]
                    answers_result[q_num] = chosen_opt
                    # Vẽ màu xanh lá cho ô được chọn
                    cv2.circle(debug_img, tuple(q_coords[max_ratio_idx]), 6, (0, 255, 0), 2)
                else:
                    answers_result[q_num] = "TRUNG"  # Tô trùng nhiều đáp án
                    # Vẽ màu đỏ cảnh báo tô trùng
                    for o_idx, r_val in enumerate(q_ratios):
                        if r_val > 0.35:
                            cv2.circle(debug_img, tuple(q_coords[o_idx]), 6, (0, 0, 255), 2)
            else:
                answers_result[q_num] = "TRONG"  # Không tô câu trả lời nào
                
        # 6. Encode ảnh debug để gửi lên giao diện
        _, buffer = cv2.imencode('.jpg', debug_img)
        import base64
        debug_base64 = base64.b64encode(buffer).decode('utf-8')
        
        has_error = "?" in cccd_str or "?" in dethi_str or any(ans in ["TRUNG", "TRONG"] for ans in answers_result.values())
        
        sheet_data = {
            "cccd": cccd_str,
            "de_thi": dethi_str,
            "answers": answers_result,
            "has_error": has_error
        }
        
        return sheet_data, None, debug_base64
