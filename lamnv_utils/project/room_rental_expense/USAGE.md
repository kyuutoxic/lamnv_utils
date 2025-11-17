# Hướng Dẫn Sử Dụng Module Room Rental Expense

Module giúp người thuê trọ tự quản lý chi phí phòng trọ: phòng, chỉ số công tơ, hóa đơn, thanh toán, chi phí khác, tiền cọc và sự cố.  
Tài liệu này mô tả chi tiết các menu, quy trình và một số quy tắc quan trọng trong module.

---

## 1. Cấu Trúc Menu

- **Quản Lý Phòng Trọ**
  - **Quản Lý**
    - `Phòng Trọ` (`rental.room`)
    - `Chỉ Số Công Tơ` (`meter.reading`)
    - `Hóa Đơn` (`room.invoice`)
  - **Chi Phí & Khác**
    - `Chi Phí` (`room.expense`)
    - `Tiền Cọc` (`room.deposit`)
    - `Sự Cố` (`room.issue`)
  - **Cấu Hình**
    - `Giá Tiện Ích` (`room.config`)
    - `Lịch Sử Phòng` (`room.history`)
  - **Báo Cáo**
    - `Hóa Đơn` (pivot/graph/list)
    - `Chi Phí` (pivot/graph/list)

Từ menu **Phòng Trọ**, bạn có thể truy cập nhanh toàn bộ dữ liệu liên quan tới một phòng: hóa đơn, chỉ số, chi phí, cọc, sự cố.

---

## 2. Thiết Lập Ban Đầu

### 2.1. Tạo cấu hình giá tiện ích (`room.config`)

1. Vào **Quản Lý Phòng Trọ → Cấu Hình → Giá Tiện Ích**.
2. Mỗi bản ghi tương ứng với một mốc giá cho một phòng:
   - `Phòng Trọ`
   - `Ngày Có Hiệu Lực` (`effective_date`)
   - `Giá Điện`, `Giá Nước`
   - `Wifi`, `Rác`, `Gửi Xe`, `Tiện Ích Khác`
3. Một phòng có thể có nhiều cấu hình theo thời gian.  
   Khi tạo hóa đơn, hệ thống sẽ lấy cấu hình **mới nhất** của phòng đó có `effective_date <= ngày/tháng hóa đơn`.

Nếu phòng chưa có `room.config`, hệ thống sẽ dùng giá mặc định trong `ir.config_parameter` (khai báo sẵn trong `room_config_data.xml`).

### 2.2. Tạo phòng trọ (`rental.room`)

1. Vào **Quản Lý → Phòng Trọ** → bấm **Tạo**.
2. Điền:
   - Thông tin chung: Tên phòng, số phòng, tên nhà, địa chỉ, diện tích, loại phòng.
   - Thời gian thuê: Ngày bắt đầu / Ngày kết thúc (nếu có).
   - Chủ phòng: Tên, điện thoại, email, ngân hàng, tài khoản, cờ “Yêu Thích”.
   - `Tiền Thuê Mặc Định`: dùng để tự điền `rent_amount` trên hóa đơn.
3. Tab khác trong form phòng:
   - **Tài Chính**: tổng tiền hóa đơn, đã trả, còn nợ, tổng chi phí.
   - **Hóa Đơn**: danh sách hóa đơn của phòng.
   - **Chỉ Số Công Tơ**: lịch sử ghi công tơ.
   - **Chi Phí**, **Tiền Cọc**, **Sự Cố**: các bản ghi liên quan.

> Lưu ý: Khi tạo hóa đơn/chỉ số/chi phí/cọc/sự cố từ các tab trong phòng, hệ thống tự gắn `room_id` qua context, nên không cần chọn lại phòng.

---

## 3. Ghi Chỉ Số Công Tơ (`meter.reading`)

### 3.1. Ghi chỉ số mới

1. Từ **Phòng Trọ**:
   - Mở phòng → tab **Chỉ Số Công Tơ** → bấm **Thêm**.  
   (Hoặc qua menu **Chỉ Số Công Tơ** → **Tạo** rồi chọn phòng.)
2. Điền:
   - `Ngày Ghi Chỉ Số` – hệ thống tự tính `Tháng Ghi Chỉ Số (MM/YYYY)`.
   - `Số Điện/Nước Tháng Trước` sẽ tự gợi ý theo lần ghi gần nhất của phòng.
   - `Số Điện/Nước Hiện Tại`.
3. Nếu thay công tơ:
   - Tick `Đã Thay Công Tơ Điện/Nước?`.
   - Nhập `Chỉ Số Cuối Công Tơ Cũ`. Hệ thống sẽ tính:
     - Phần cũ: `max(last_old - previous, 0)`
     - Cộng với chỉ số mới.
4. Nếu chủ trọ đưa thẳng số “lượng sử dụng”:
   - Tick `Nhập Tay Điện Sử Dụng` hoặc `Nhập Tay Nước Sử Dụng`.
   - Nhập giá trị usage, trường `electric_usage`/`water_usage` sẽ cho phép sửa trực tiếp.

Bạn có thể đính kèm ảnh công tơ và ghi chú chi tiết trong các field ghi chú.

### 3.2. Ràng buộc và hành vi đặc biệt

- Hệ thống cảnh báo nếu:
  - Không tick “Đã thay công tơ” mà số hiện tại < số tháng trước.
- Khi thay đổi `room_id` hoặc `reading_date`, hệ thống tự tìm chỉ số trước đó để gợi ý `electric_previous`/`water_previous`.
- **Khi chỉ số đã gắn với hóa đơn (`invoice_id` có giá trị):**
  - Không thể sửa `room_id`, `reading_date`, các số điện/nước và cờ override trên form (chúng thành readonly).
  - Không thể xóa bản ghi – `unlink` sẽ chặn với thông báo yêu cầu xử lý hóa đơn trước.

---

## 4. Tạo & Quản Lý Hóa Đơn (`room.invoice`)

### 4.1. Tạo hóa đơn từ Phòng Trọ (khuyến nghị)

1. Mở phòng → tab **Hóa Đơn** → bấm **Thêm**.
2. Form hóa đơn:
   - `room_id` tự điền theo phòng.
   - Khi chọn/chỉnh `invoice_month` hoặc `invoice_date`, hệ thống:
     - Tự điền `rent_amount` bằng `Tiền Thuê Mặc Định` nếu chưa nhập.
     - Dùng `room._get_active_config(reference_date)` để lấy `room.config` phù hợp.
     - Gán:
       - `electric_price_per_unit`, `water_price_per_unit`,
       - `utilities_amount` (wifi + rác + xe + tiện ích khác),
       - `applied_config_id` = bản ghi `room.config` được áp dụng.
3. Nếu đã có chỉ số công tơ cho tháng đó:
   - Chọn `meter_reading_id` (lọc theo phòng).
   - Onchange sẽ copy `electric_usage`, `water_usage` và, nếu hóa đơn chưa có `invoice_month`, sẽ set theo `reading_month`.

### 4.2. Tạo hóa đơn từ menu Hóa Đơn

1. Vào **Quản Lý → Hóa Đơn** → **Tạo**.
2. Chọn `room_id`, `invoice_month`/`invoice_date`.  
   Các bước áp giá và set `applied_config_id` giống như khi tạo từ phòng.

### 4.3. Các field và công thức chính

- `electric_amount = electric_usage × electric_price_per_unit`
- `water_amount = water_usage × water_price_per_unit`
- `utilities_amount`: tổng wifi + rác + xe + tiện ích khác (có thể sửa tay).
- `subtotal = rent_amount + electric_amount + water_amount + utilities_amount + other_charges`
- `total_amount = subtotal - discount_amount`
- `remaining_amount = total_amount - paid_amount`

Tab “Tóm Tắt” hiển thị thêm `manual_breakdown` – mô tả chi tiết dạng text (VD: “Nước: 4 - 0 = 4 x 20.000 = 80.000”).

### 4.4. Trạng thái và quyền sửa

- Trạng thái (`statusbar`):
  - `draft` → `pending` → `partially_paid` → `paid` / `overdue` → `canceled`
  - Nút:
    - **Xác Nhận**: chỉ khi `draft`.
    - **Đã Thanh Toán**: khi `pending`/`partially_paid`/`overdue`.
    - **Hủy**: ẩn khi đã `paid` hoặc `canceled`.
- Khi **không còn `draft`**:
  - Các field cơ sở (`room_id`, `invoice_month`, `invoice_date`, `due_date`, `meter_reading_id`) readonly.
  - Các số tiền/usage (`rent_amount`, giá/usage điện nước, `utilities_amount`, `other_charges`, `discount_amount`) readonly.
  - Bạn vẫn chỉnh `notes`, xem breakdown, in PDF bình thường.

### 4.5. Cron nhắc hạn và quá hạn

- Cron **Room Invoice Status Update** chạy hằng ngày:
  - Tự cập nhật trạng thái `overdue` cho hóa đơn quá hạn chưa thanh toán.
  - Tạo activity “Nhắc thanh toán hóa đơn” trước `N` ngày đến hạn,
    với `N` lấy từ tham số `room_rental_expense.reminder_days` (mặc định 3).

---

## 5. Chi Phí Khác, Tiền Cọc, Sự Cố

### 5.1. Chi phí khác (`room.expense`)

- Dùng để ghi lại các chi phí như sửa chữa, vệ sinh, mua đồ dùng…  
- Các field chính: `room_id`, `expense_date`, `category`, `description`, `amount`, `receipt_image`.
- Trong form Phòng Trọ, tab **Chi Phí** hiển thị toàn bộ chi phí của phòng đó.

### 5.2. Tiền cọc (`room.deposit`)

- Lưu tiền cọc đầu vào và việc hoàn cọc:
  - `deposit_amount`, `deposit_date`, `expected_return_date`,
  - `status` (pending/confirmed/partial_return/fully_returned/disputed),
  - `return_date`, `return_amount`, `receipt_image`.

### 5.3. Sự cố (`room.issue`)

- Ghi lại các vấn đề xảy ra trong phòng:
  - `issue_date`, `category`, `description`, `severity`, `status`,
  - `reported_date`, `resolved_date`, `issue_image`, `notes`.
- Hữu ích để theo dõi lịch sử sửa chữa và làm bằng chứng nếu có tranh chấp.

---

## 6. Lịch Sử Phòng (`room.history`)

- Dùng để tổng hợp các phòng đã thuê (không gắn trực tiếp vào workflow chính).
- Có thể liên kết với `rental.room` để:
  - Tính `total_spent` = tổng `total_amount` hóa đơn + tổng `amount` chi phí của phòng đó.
  - Ghi nhận đánh giá chủ phòng, mức giá trung bình, thời gian thuê.

---

## 7. Ghi Chú Quan Trọng

- **Về cấu hình giá:**
  - Đừng dùng field `applied_config_id` như “current config của phòng”; nó ghi lại **config đã áp dụng tại thời điểm tạo hóa đơn** để giữ lịch sử giá.
  - Khi giá thay đổi, hãy tạo `room.config` mới với `effective_date` mới,
    không sửa bản ghi cũ nếu muốn giữ lịch sử.

- **Về chỉnh sửa sau khi đã lên hóa đơn:**
  - Chỉ số công tơ đã gắn hóa đơn: không được sửa số liệu, không được xóa.
  - Hóa đơn đã rời `draft`: không sửa được các con số gốc, chỉ thêm ghi chú.

- **Về tạo dữ liệu:**
  - Ưu tiên tạo chỉ số và hóa đơn từ **form Phòng Trọ** để context `room_id` được set đúng, tránh quên chọn phòng.
  - Các tab trong Phòng Trọ đều đã được cấu hình để tự gắn `default_room_id`.

Nếu muốn mở rộng module, xem thêm đặc tả chi tiết trong `ROOM_MANAGEMENT_SPEC.md`.
