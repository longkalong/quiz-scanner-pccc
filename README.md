# OMR Quiz Scanner & Printer

Hệ thống chấm thi trắc nghiệm bằng ảnh quét OMR (A4) kết hợp công cụ in điểm số trực tiếp lên phiếu thi vật lý. Dự án được tối ưu hóa cho giáo viên Việt Nam, giải quyết triệt để vấn đề nhập liệu và in điểm thủ công.

## 🌟 Tính năng nổi bật

1. **Nhận dạng OMR chính xác cao:**
   - Hỗ trợ căn thẳng ảnh quét bị nghiêng/lệch bằng thuật toán Warp Perspective dựa trên 4 điểm định vị hình vuông màu đen ở 4 góc.
   - Nhận diện CCCD (12 chữ số), Mã đề thi (4 chữ số) và 30 câu hỏi trắc nghiệm (A, B, C, D) bằng xử lý ảnh nhị phân động (Dynamic Thresholding).

2. **Tích hợp Excel thông minh (XLSX):**
   - Đọc danh sách thí sinh từ tệp `data/candidates.xlsx` hỗ trợ nhiều sheets (nhiều lớp khác nhau).
   - Tự động đăng ký thêm thí sinh mới trực tiếp trên giao diện và ghi đè lưu trữ vào file Excel gốc.
   - Xuất file Excel kết quả, tự động điền cột điểm và giữ nguyên cấu trúc phân chia sheet lớp học ban đầu.

3. **Giao diện Xem & Sửa trực quan:**
   - **Mặt nạ kiểm tra:** Khoanh vòng tròn màu đỏ to bao quanh đáp án đúng giúp giáo viên dễ dàng kiểm tra bằng mắt thường.
   - **Chia 3 cột:** Khớp hoàn toàn với cấu trúc trên phiếu giấy để dễ đối chiếu.
   - **Thống kê Đúng/Sai thời gian thực:** Nhảy số thống kê câu đúng/sai tự động trên mỗi cột khi click thay đổi đáp án.

4. **In Điểm số Lên Phiếu Vật Lý (Xuất Word):**
   - Sinh tệp Word `.docx` chứa điểm số đỏ cỡ lớn được căn chỉnh đúng vị trí ô chữ nhật trên phiếu giấy.
   - Khi cho tập phiếu giấy vào khay nạp của máy in và in tệp Word này, điểm số sẽ tự động in đè vào đúng ô trên giấy, không cần viết tay.

## 📁 Cấu trúc thư mục

* `app.py`: Flask Web Server và APIs.
* `omr_processor.py`: Engine cốt lõi xử lý ảnh, dò điểm định vị và nhận diện OMR.
* `generate_template.py`: Script xuất file thiết kế gốc OMR chuẩn (PNG/PDF).
* `simulate_filled_sheet.py`: Script tự động sinh bài làm mẫu đã tô để chạy thử nghiệm.
* `templates/index.html`: Giao diện Web Dashboard.
* `data/`: Thư mục lưu cấu hình tọa độ, đáp án mẫu và danh sách thí sinh Excel.

## 🚀 Hướng dẫn cài đặt & Chạy thử

1. **Cài đặt thư viện:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Chạy ứng dụng:**
   ```bash
   python app.py
   ```
   Sau đó truy cập địa chỉ: `http://127.0.0.1:5000` trên trình duyệt.

3. **Chạy thử nghiệm:**
   - Nút **"Cấu hình Tọa độ"** và **"Chấm bài thi"** được đặt gọn gàng trên Header.
   - Các tệp bài làm mẫu thử nghiệm (`phieu_mau_1.png` đến `phieu_mau_5.png`) sẽ tự động được sinh ra trong thư mục dự án khi bạn lưu cấu hình tọa độ. Bạn chỉ cần kéo thả chúng vào giao diện để kiểm tra!
