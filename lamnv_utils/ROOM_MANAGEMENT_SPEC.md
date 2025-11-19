# Specification: Module Quản Lý Chi Phí Phòng Trọ (Cá Nhân)

## I. TỔNG QUAN MODULE
- **Mục đích**: Giúp người thuê trọ quản lý các khoản chi phí phòng trọ hàng tháng (tiền phòng, điện, nước, tiện ích) và lịch sử thanh toán
- **Đối tượng sử dụng**: Người thuê trọ cá nhân
- **Phạm vi**: Quản lý 1 phòng trọ hoặc nhiều phòng (nếu thuê nhiều chỗ)

---

## II. MODELS (BẢNG DỮ LIỆU)

### A. 1. Model: Phòng Trọ (rental_room)
**Chức năng**: Lưu trữ thông tin chi tiết về phòng trọ bạn đang thuê

**Fields**:
- `name` (Char) - Tên phòng (VD: "Phòng 101 - Lê Văn Sỹ") [required]
- `room_number` (Char) - Số phòng (VD: "101", "A1")
- `building_name` (Char) - Tên nhà/khu trọ (VD: "Nhà trọ Nguyễn Văn A", "KTX Nam")
- `address` (Text) - Địa chỉ đầy đủ
- `landlord_name` (Char) - Tên chủ phòng
- `landlord_phone` (Char) - Số điện thoại chủ phòng
- `landlord_email` (Char) - Email chủ phòng
- `area` (Float) - Diện tích (m²)
- `room_type` (Selection) - Loại phòng: "single", "double", "studio", "shared"
- `start_date` (Date) - Ngày bắt đầu thuê
- `end_date` (Date) - Ngày kết thúc thuê (nếu có)
- `description` (Text) - Mô tả phòng (có những gì)
- `utilities_included` (Text) - Tiện ích bao gồm trong giá (nước, điện, wifi...)
- `note` (Text) - Ghi chú khác
- `image` (Binary) - Ảnh phòng

**Relationships**:
- `invoices` (One2Many) → Model: Hóa Đơn (room_invoice)
- `meter_readings` (One2Many) → Model: Chỉ số công tơ (meter_reading)
- `expenses` (One2Many) → Model: Chi phí khác (room_expense)

---

### A. 2. Model: Chỉ Số Công Tơ (meter_reading)
**Chức năng**: Ghi lại chỉ số điện, nước hàng tháng mà bạn ghi được từ công tơ

**Fields**:
- `room_id` (Many2One) → rental_room [required]
- `reading_date` (Date) - Ngày ghi chỉ số [required]
- `reading_month` (Char) - Tháng ghi chỉ số (MM/YYYY) - auto-compute [required]
- **Điện**:
  - `electric_previous` (Float) - Số điện tháng trước (kWh)
  - `electric_current` (Float) - Số điện hiện tại (kWh) [required]
  - `electric_usage` (Float) - Lượng điện sử dụng (kWh) - auto-compute (current - previous)
  - `electric_meter_replaced` (Boolean) - ✓ Đã thay công tơ? [default: False]
  - `electric_image` (Binary) - Ảnh công tơ điện (chụp hình công tơ để làm chứng)
  - `electric_replacement_note` (Text) - Ghi chú thay công tơ (VD: "Thay công tơ cũ vào ngày 15/11, số cũ: 12345, số mới: 00123")
- **Nước**:
  - `water_previous` (Float) - Số nước tháng trước (m³)
  - `water_current` (Float) - Số nước hiện tại (m³) [required]
  - `water_usage` (Float) - Lượng nước sử dụng (m³) - auto-compute (current - previous)
  - `water_meter_replaced` (Boolean) - ✓ Đã thay công tơ? [default: False]
  - `water_image` (Binary) - Ảnh công tơ nước (chụp hình công tơ để làm chứng)
  - `water_replacement_note` (Text) - Ghi chú thay công tơ (VD: "Thay công tơ cũ vào ngày 15/11, số cũ: 5678, số mới: 00045")
- `notes` (Text) - Ghi chú (VD: "Máy lạnh bị hỏng nên dùng quạt, điện dùng ít")

---

### A. 3. Model: Hóa Đơn (room_invoice)
**Chức năng**: Lưu trữ hóa đơn tiền phòng hàng tháng - có thể tự tạo hoặc import từ chủ phòng

**Fields**:
- `room_id` (Many2One) → rental_room [required]
- `invoice_number` (Char) - Số hóa đơn (VD: "INVOICE-2025-01", auto-generate)
- `invoice_month` (Char) - Tháng hóa đơn (MM/YYYY) [required]
- `invoice_date` (Date) - Ngày lập hóa đơn
- `due_date` (Date) - Hạn thanh toán
- `status` (Selection) - Trạng thái: "draft", "pending", "paid", "partially_paid", "overdue", "canceled" 
- **Chi tiết hóa đơn**:
  - `rent_amount` (Float) - Tiền thuê (VND) [required]
  - `electric_price_per_unit` (Float) - Giá điện/kWh (VND/kWh)
  - `electric_usage` (Float) - Điện sử dụng (kWh) - link từ meter_reading
  - `electric_amount` (Float) - Tiền điện (VND) - auto-compute
  - `water_price_per_unit` (Float) - Giá nước/m³ (VND/m³)
  - `water_usage` (Float) - Nước sử dụng (m³) - link từ meter_reading
  - `water_amount` (Float) - Tiền nước (VND) - auto-compute
  - `utilities_amount` (Float) - Tiền tiện ích khác: wifi, rác, gửi xe (VND)
  - `other_charges` (Float) - Phí khác/phạt (VND)
  - `subtotal` (Float) - Tổng cộng (VND) - auto-compute
  - `discount_amount` (Float) - Chiết khấu/giảm giá (VND)
  - `total_amount` (Float) - Tổng thanh toán (VND) - auto-compute
- `paid_amount` (Float) - Số tiền đã thanh toán (VND)
- `remaining_amount` (Float) - Số tiền còn lại (VND) - auto-compute
- `notes` (Text) - Ghi chú

**Relationships**:
- Không có relationship phức tạp (thanh toán được quản lý trực tiếp trong hóa đơn)

---

### A. 4. Model: Chi Phí Khác (room_expense)
**Chức năng**: Quản lý chi phí phòng phát sinh khác ngoài hóa đơn hàng tháng (sửa chữa, vệ sinh, mua đồ...)

**Fields**:
- `room_id` (Many2One) → rental_room [required]
- `expense_date` (Date) - Ngày chi phí [required]
- `category` (Selection) - Danh mục: 
  - "repair" (sửa chữa: quạt, tủ lạnh...)
  - "cleaning" (vệ sinh hàng tháng, dọn dẹp)
  - "supplies" (mua đồ sử dụng: bóng đèn, chổi, quay, xà phòng...)
  - "maintenance" (bảo trì: kiểm tra điều hòa, lau rửa công tơ...)
  - "damage_fee" (phí hư hỏng: phá hỏng đồ nhà chủ)
  - "other" (khác)
- `description` (Text) - Mô tả chi tiết (VD: "Sửa quạt trần", "Mua bóng đèn LED") [required]
- `amount` (Float) - Số tiền (VND) [required]
- `notes` (Text) - Ghi chú thêm
- `receipt_image` (Binary) - Ảnh hóa đơn/biên lai

**Relationships**:
- Không có relationship phức tạp

---

### A. 5. Model: Cấu Hình Phòng (room_config)
**Chức năng**: Lưu giá điện, nước hiện tại để tính hóa đơn nhanh

**Fields**:
- `room_id` (Many2One) → rental_room [required]
- `effective_date` (Date) - Ngày có hiệu lực [required]
- `electric_price` (Float) - Giá điện/kWh (VND/kWh) [required]
- `water_price` (Float) - Giá nước/m³ (VND/m³) [required]
- `wifi_price` (Float) - Giá Wifi/tháng (VND)
- `trash_fee` (Float) - Phí rác/tháng (VND)
- `parking_fee` (Float) - Phí gửi xe/tháng (VND)
- `other_utilities_price` (Float) - Giá tiện ích khác/tháng (VND)
- `notes` (Text) - Ghi chú

---

### A. 6. Model: Lịch Sử Phòng (room_history) [Optional - để theo dõi các phòng đã thuê]
**Chức năng**: Ghi lại lịch sử các phòng trọ mà bạn đã thuê

**Fields**:
- `name` (Char) - Tên/địa chỉ phòng [required]
- `from_date` (Date) - Từ ngày
- `to_date` (Date) - Đến ngày
- `landlord_name` (Char) - Tên chủ phòng
- `landlord_phone` (Char) - Số điện thoại chủ phòng
- `avg_rent` (Float) - Giá thuê trung bình/tháng
- `notes` (Text) - Nhận xét về phòng/chủ phòng

---

## III. CHỨC NĂNG CHÍNH

### 1. Quản Lý Phòng Trọ Hiện Tại
- [ ] Thêm thông tin phòng trọ đang thuê
- [ ] Sửa thông tin phòng
- [ ] Lưu thông tin chủ phòng (tên, phone, email)
- [ ] Xem chi tiết phòng
- [ ] Lưu ảnh phòng

### 2. Ghi Chỉ Số Công Tơ
- [ ] Ghi lại chỉ số điện, nước hàng tháng
- [ ] Auto-calculate: `electric_usage = electric_current - electric_previous`
- [ ] Auto-calculate: `water_usage = water_current - water_previous`
- [ ] Cảnh báo nếu chỉ số giảm (nhập sai)
- [ ] Liệt kê chỉ số theo tháng
- [ ] Xem biểu đồ sử dụng điện/nước theo thời gian
- [ ] Export chỉ số công tơ

### 3. Quản Lý Hóa Đơn
- [ ] Tạo hóa đơn thủ công hàng tháng
- [ ] Nhập chỉ số điện, nước từ `meter_reading` vào hóa đơn
- [ ] Auto-calculate:
  - `electric_amount = electric_usage × electric_price_per_unit`
  - `water_amount = water_usage × water_price_per_unit`
  - `subtotal = rent_amount + electric_amount + water_amount + utilities_amount + other_charges`
  - `total_amount = subtotal - discount_amount`
  - `remaining_amount = total_amount - paid_amount`
- [ ] Sửa hóa đơn (draft status)
- [ ] Xóa hóa đơn (draft status)
- [ ] Liệt kê hóa đơn với bộ lọc:
  - Theo tháng
  - Theo trạng thái (draft, pending, paid, overdue)
  - Theo khoảng thời gian
- [ ] Xem chi tiết hóa đơn (layout chuyên nghiệp)
- [ ] Thay đổi trạng thái hóa đơn (draft → pending → paid)
- [ ] Ghi nhận thanh toán trực tiếp trong hóa đơn (field `paid_amount`)
- [ ] Export PDF hóa đơn
- [ ] In hóa đơn
- [ ] Thêm ghi chú trên hóa đơn (vấn đề với nước, điện...)

### 4. Quản Lý Chi Phí Khác
- [ ] Thêm chi phí phát sinh (sửa quạt, mua bóng đèn, vệ sinh...)
- [ ] Sửa chi phí
- [ ] Xóa chi phí
- [ ] Liệt kê chi phí với bộ lọc:
  - Theo danh mục (repair, cleaning, supplies...)
  - Theo tháng/năm
  - Theo khoảng thời gian
- [ ] Xem chi tiết chi phí
- [ ] Tải ảnh hóa đơn/biên lai chi phí
- [ ] Tính tổng chi phí theo tháng/năm
- [ ] Export danh sách chi phí

### 5. Cấu Hình Giá Tiện Ích
- [ ] Lưu giá điện, nước hiện tại
- [ ] Cấu hình giá wifi, phí rác, phí gửi xe, tiện ích khác
- [ ] Lịch sử thay đổi giá (để so sánh)
- [ ] Đặt ngày có hiệu lực

### 6. Báo Cáo & Thống Kê
- [ ] **Báo cáo hóa đơn tháng**: tổng tiền phòng, tiền điện, tiền nước, tổng cộng
- [ ] **Báo cáo thanh toán**: tổng đã thanh toán, nợ còn lại, hóa đơn quá hạn
- [ ] **Báo cáo chi phí**: tổng chi phí theo danh mục, chi phí trung bình/tháng
- [ ] **Báo cáo sử dụng điện/nước**: lượng sử dụng theo tháng, so sánh với tháng trước
- [ ] **Báo cáo tổng hợp**: tổng doanh thu chi tiêu theo tháng/năm
- [ ] **Thống kê hóa đơn**: hóa đơn chưa thanh toán, hóa đơn quá hạn
- [ ] Export báo cáo ra Excel, PDF
- [ ] Biểu đồ doanh thu, chi phí, nợ theo tháng
- [ ] Biểu đồ sử dụng điện/nước theo tháng

### 7. Thông Báo & Nhắc Nhở
- [ ] Nhắc nhở hóa đơn sắp đến hạn (N ngày trước)
- [ ] Cảnh báo hóa đơn quá hạn
- [ ] Nhắc nhở thanh toán qua notification

### 8. Lịch Sử Phòng Trọ
- [ ] Ghi lại các phòng trọ đã/đang thuê
- [ ] Lưu thông tin chủ phòng (để liên hệ lại)
- [ ] Ghi chú về chất lượng phòng, chủ phòng
- [ ] Tính toán tổng chi phí cho mỗi phòng

### 9. Cấu Hình Chung
- [ ] Lưu thông tin cá nhân (tên, email, phone)
- [ ] Cấu hình template hóa đơn
- [ ] Cấu hình thông báo tự động

### 10. Công Cụ Khác
- [ ] Import dữ liệu từ Excel (hóa đơn, chi phí)
- [ ] Export danh sách hóa đơn, thanh toán, chi phí theo định dạng Excel
- [ ] Backup dữ liệu
- [ ] Xóa dữ liệu cũ (tuỳ chọn)

### 11. Tính Năng Bổ Sung (Recommended)

#### 11.1 Model: Tiền Cọc (room_deposit)
**Chức năng**: Quản lý tiền cọc - theo dõi khi nào bạn đã nộp, bao nhiêu tiền, và khi nào sẽ được hoàn lại

**Fields**:
- `room_id` (Many2One) → rental_room [required]
- `deposit_amount` (Float) - Số tiền cọc (VND) [required]
- `deposit_date` (Date) - Ngày nộp tiền cọc [required]
- `expected_return_date` (Date) - Dự kiến hoàn tiền (thường là khi hết hợp đồng)
- `status` (Selection) - Trạng thái: "pending", "confirmed", "partial_return", "fully_returned", "disputed"
- `return_date` (Date) - Ngày thực tế hoàn tiền
- `return_amount` (Float) - Số tiền thực tế được hoàn
- `notes` (Text) - Ghi chú (VD: "Hoàn 4.5M, chủ trọ giữ 0.5M do hư đồ")
- `receipt_image` (Binary) - Ảnh biên lai nộp cọc

**Tại sao cần**: Tiền cọc có khi bị chủ trọ giữ lại, hoặc hoàn không đủ. Bạn cần track để không bị mất

#### 11.2 Thêm Field: Mối Liên Hệ Người Thuê
**Chức năng**: Lưu lại đường dây liên lạc khẩn cấp với chủ phòng

**Fields thêm vào rental_room**:
- `landlord_bank_account` (Char) - Tài khoản ngân hàng chủ trọ (để chuyển tiền)
- `landlord_bank_name` (Char) - Tên ngân hàng (VD: "Vietcombank", "Techcombank")
- `landlord_favorite` (Boolean) - Đánh dấu số điện thoại/email chủ trọ

**Tại sao cần**: Bạn cần biết chuyển tiền cho chủ trọ qua ngân hàng nào, account nào

#### 11.3 Thêm Tính Năng: Lịch Thanh Toán Tự Động Nhắc Nhở
**Chức năng**: Hệ thống tự động nhắc nhở bạn thanh toán trước deadline

**Chi tiết**:
- [ ] Cấu hình ngày "hạn thanh toán" trong hóa đơn
- [ ] Hệ thống tự động gửi notification N ngày trước hạn (VD: 3 ngày)
- [ ] Liệt kê tất cả hóa đơn "sắp đến hạn" và "quá hạn" trên dashboard
- [ ] Cảnh báo nếu có hóa đơn quá hạn (chưa thanh toán)

**Tại sao cần**: Bạn sẽ không bao giờ quên thanh toán hóa đơn

#### 11.4 Thêm Model: Ghi Chú Sự Cố (room_issue)
**Chức năng**: Ghi lại những sự cố, vấn đề xảy ra trong phòng để liên hệ với chủ trọ

**Fields**:
- `room_id` (Many2One) → rental_room [required]
- `issue_date` (Date) - Ngày phát hiện sự cố [required]
- `category` (Selection) - Loại sự cố:
  - "water_leak" (rò nước)
  - "electric_problem" (vấn đề điện)
  - "broken_furniture" (đồ đạc hỏng: quạt, tủ lạnh...)
  - "pest" (sâu bọ, tařn)
  - "noise" (ồn ào)
  - "temperature" (lạnh/nóng không thoải mái)
  - "other" (khác)
- `description` (Text) - Mô tả chi tiết [required]
- `severity` (Selection) - Mức độ: "low", "medium", "high", "critical"
- `status` (Selection) - Trạng thái: "reported", "acknowledged", "in_progress", "resolved"
- `reported_date` (Date) - Ngày báo cáo cho chủ trọ
- `resolved_date` (Date) - Ngày được sửa chữa
- `issue_image` (Binary) - Ảnh vấn đề (để gửi cho chủ trọ)
- `notes` (Text) - Ghi chú

**Tại sao cần**: Bạn cần track những sự cố để:
- Không quên gửi yêu cầu sửa chữa cho chủ trọ
- Nếu chủ trọ tính tiền sửa chữa, bạn có bằng chứng
- Theo dõi độ uy tín của chủ trọ (sửa chữa nhanh hay chậm)

#### 11.5 Dashboard Tổng Hợp
**Chức năng**: Một màn hình tổng quát hiển thị tình hình tài chính của bạn

**Hiển thị**:
- 📊 **Thẻ thông tin nhanh (KPI Cards)**:
  - Tiền hóa đơn tháng này: X.XXX VND
  - Tiền chưa thanh toán: X.XXX VND (có cảnh báo nếu quá hạn)
  - Tiền tiện ích: X.XXX VND
  - Tổng chi phí (tất cả hạng mục): X.XXX VND
  
- 📈 **Biểu đồ nhanh**:
  - Xu hướng tiền thanh toán (6 tháng gần đây)
  - So sánh sử dụng điện/nước (6 tháng gần đây)
  - Danh mục chi phí (pie chart)
  
- 📋 **Danh sách nhanh**:
  - Hóa đơn sắp đến hạn (3 hóa đơn gần nhất)
  - Sự cố chưa được sửa chữa (nếu có)
  - Những ghi chú quan trọng

- 📌 **Quick Actions**:
  - "Ghi chỉ số mới" (button nhanh)
  - "Tạo hóa đơn" (button nhanh)
  - "Ghi nhận thanh toán" (button nhanh)

**Tại sao cần**: Bạn có cái nhìn toàn bộ tình hình tài chính ngay khi mở app, không cần vào từng module

---

---

## IV. VIEWS (GIAO DIỆN)

### 1. Views cho Phòng Trọ (rental_room)
- [ ] List View: Xem danh sách phòng đang/đã thuê
- [ ] Form View: Chi tiết phòng + thông tin chủ phòng + tab hóa đơn, chỉ số, chi phí
- [ ] Dashboard: Phòng đang thuê, ngày hết hạn

### 2. Views cho Chỉ Số Công Tơ (meter_reading)
- [ ] List View: Danh sách chỉ số, filter theo tháng
- [ ] Form View: Chi tiết chỉ số (nhập điện, nước)
- [ ] Graph View: Biểu đồ sử dụng điện/nước theo tháng

### 3. Views cho Hóa Đơn (room_invoice)
- [ ] List View: Danh sách hóa đơn, filter theo tháng/trạng thái
- [ ] Form View: Chi tiết hóa đơn (layout chuyên nghiệp như hóa đơn thật)
- [ ] Pivot View: Báo cáo doanh thu chi tiêu
- [ ] Graph View: Biểu đồ doanh thu, chi tiêu

### 4. Views cho Chi Phí (room_expense)
- [ ] List View: Danh sách chi phí, filter theo danh mục/tháng
- [ ] Form View: Chi tiết chi phí (có field tải ảnh hóa đơn)
- [ ] Graph View: Biểu đồ chi phí theo danh mục

### 5. Views cho Cấu Hình (room_config)
- [ ] List View: Danh sách giá tiện ích
- [ ] Form View: Chi tiết giá (để cập nhật giá điện, nước...)

### 6. Views cho Lịch Sử (room_history)
- [ ] List View: Danh sách phòng đã thuê
- [ ] Form View: Chi tiết phòng (tên, chủ phòng, thời gian, giá tiền)

---

## V. WORKFLOWS (QUY TRÌNH CÔNG VIỆC)

### 1. Quy trình quản lý phòng trọ mới
```
Thêm phòng mới → Lưu thông tin chủ phòng → Lưu giá tiện ích → Bắt đầu ghi chỉ số
```

### 2. Quy trình tính tiền hàng tháng
```
Ghi chỉ số công tơ (điện, nước) → Tạo hóa đơn → Xem chi tiết → Ghi nhận thanh toán trực tiếp trong hóa đơn → Update trạng thái
```

### 3. Quy trình ghi nhận chi phí phát sinh
```
Ghi nhận chi phí (sửa chữa, vệ sinh...) → Tải ảnh hóa đơn → Theo dõi chi phí theo tháng
```

### 4. Quy trình kiểm tra tài chính
```
Xem báo cáo hóa đơn → Xem báo cáo thanh toán (nợ) → Xem báo cáo chi phí → Tổng hợp doanh thu/chi tiêu
```

---

## VI. VALIDATIONS & CONSTRAINTS

- [ ] Số phòng không được trùng lặp
- [ ] Chỉ số công tơ phải lớn hơn chỉ số tháng trước **TRỪ khi đã thay công tơ**
  - Nếu `electric_meter_replaced = True` → không validate chỉ số giảm
  - Nếu `electric_meter_replaced = False` → cảnh báo nếu chỉ số giảm
- [ ] Tương tự với nước: kiểm tra `water_meter_replaced`
- [ ] Ngày kết thúc phòng phải lớn hơn ngày bắt đầu (nếu có)
- [ ] Hóa đơn không được xóa nếu đã thanh toán
- [ ] Không được thêm thanh toán vượt quá tổng hóa đơn
- [ ] Giá điện, nước phải > 0
- [ ] Không được tạo hóa đơn nếu không có chỉ số công tơ
- [ ] Email phải đúng định dạng (nếu có)
- [ ] Số điện thoại phải đúng định dạng

---

## VI.B. HƯỚNG XỬ LÝ KHI THAY CÔNG TƠ

### Trường Hợp 1: Thay Công Tơ Điện / Nước
**Khi nào xảy ra**: Công tơ bị hỏng, chính phủ yêu cầu thay đổi, hoặc chủ trọ thay mới

**Cách xử lý trong hệ thống**:
```
Khi ghi chỉ số trong tháng có thay công tơ:
1. Tick ✓ vào checkbox "Đã thay công tơ?" (electric_meter_replaced = True)
2. Nhập chỉ số cũ (trước khi thay): electric_previous = 12345 (chỉ số cuối cùng công tơ cũ)
3. Nhập chỉ số mới (sau khi thay): electric_current = 00123 (chỉ số công tơ mới, thường là nhỏ)
4. Ghi chú chi tiết: "Thay công tơ vào ngày 15/11, số cũ tối đa: 12345, số mới bắt đầu: 00123"
5. Tải ảnh: công tơ cũ trước khi thay + công tơ mới sau khi thay
```

**Tính toán lượng sử dụng**:
- Khi `electric_meter_replaced = True` → **không tính `electric_usage = electric_current - electric_previous`**
- Thay vào đó, hệ thống sẽ:
  - Lấy chỉ số tối đa công tơ cũ (thường là 99999) - giá trị trước khi thay
  - Cộng với chỉ số công tơ mới
  - **Công thức**: `electric_usage = (99999 - electric_previous) + electric_current`
  - **VD**: Công tơ cũ chỉ 12345 (tối đa là 99999), công tơ mới chỉ 123 
    → Sử dụng = (99999 - 12345) + 123 = 87654 + 123 = 87777 kWh

**Hoặc nếu chủ trọ cho biết chỉ số cụ thể**:
- Nếu chủ trọ nói "điện tháng này là 500 kWh" → nhập trực tiếp vào `electric_usage` (override)

### Trường Hợp 2: Thay Công Tơ Nhưng Không Biết Chỉ Số Cũ
**Khi nào xảy ra**: Thay công tơ trước khi ghi chỉ số tháng đó, quên không ghi lại

**Cách xử lý**:
1. Liên hệ chủ trọ hỏi chỉ số cũ trước khi thay
2. Hoặc hỏi chỉ số sử dụng ước tính cho tháng đó
3. Nhập vào field `electric_replacement_note` để ghi nhận sự thiếu thông tin

### Trường Hợp 3: Thay Công Tơ Giữa Tháng
**Khi nào xảy ra**: Công tơ hỏng và được thay giữa tháng (VD: ngày 15/11)

**Cách xử lý**:
```
Bạn sẽ có 2 bản ghi chỉ số:
1. Bản ghi ngày 15/11 (sáng): ghi chỉ số công tơ cũ trước khi thay
   - electric_current = 12345 (chỉ số cuối cùng công tơ cũ)
   - electric_meter_replaced = True
   - Ghi chú: "Công tơ hỏng, đã thay mới"
   
2. Bản ghi ngày 15/11 (chiều): ghi chỉ số công tơ mới vừa được cài đặt
   - electric_current = 00050 (chỉ số công tơ mới)
   - electric_meter_replaced = True
   - Ghi chú: "Công tơ mới được cài đặt"

Tính tiền tháng đó:
- Sử dụng từ công tơ cũ: 12345 - (chỉ số tháng trước)
- Sử dụng từ công tơ mới: 00050 - 0 = 50 kWh
- Tổng sử dụng tháng = sử dụng từ công tơ cũ + sử dụng từ công tơ mới
```

### Trường Hợp 4: Công Tơ Bị Reset/Lỗi (Không Phải Thay)
**Khi nào xảy ra**: Mất điện, công tơ tự reset, hoặc lỗi tạm thời

**Cách xử lý**:
1. Tick ✓ vào checkbox "Đã thay công tơ?" (để bỏ qua kiểm tra chỉ số giảm)
2. Ghi chú chi tiết: "Công tơ tự reset do mất điện, số trước 12345, sau khi khôi phục 12340"
3. Liên hệ chủ trọ hỏi cách tính tiền cho trường hợp này

---



## VII. SECURITY & PERMISSIONS

- [ ] Module này là **personal use** - chỉ dành cho cá nhân bạn
- [ ] Không cần phân quyền phức tạp
- [ ] Tất cả dữ liệu là riêng tư của bạn
- [ ] Lịch sử các lần sửa hóa đơn, chi phí phải được ghi nhận
- [ ] Có khả năng backup/export dữ liệu

---

## VIII. TECHNICAL REQUIREMENTS

- [ ] Sử dụng framework Odoo (ORM, Models, Views)
- [ ] Database: PostgreSQL
- [ ] Frontend: Odoo Web Interface
- [ ] Auto-compute các field: usage, amount, remaining...
- [ ] Auto-generate PDF cho hóa đơn (nếu cần in)
- [ ] Export Excel cho các báo cáo, danh sách
- [ ] Lightweight, không cần quá nhiều dependencies
- [ ] Tối ưu cho mobile view (sử dụng trên điện thoại)

---

## IX. TESTING CHECKLIST

- [ ] Unit tests cho các tính toán (rent, electric, water, total)
- [ ] Integration tests cho workflow thuê phòng
- [ ] Tests cho PDF generation
- [ ] Tests cho email sending
- [ ] Tests cho validations
- [ ] Manual testing toàn bộ flows

---

## X. FUTURE FEATURES (PHÁT TRIỂN SAU)

- [ ] Mobile app for easy invoice viewing
- [ ] QR code payment integration
- [ ] SMS/Email notifications
- [ ] Multi-room management (người ở nhiều chỗ)
- [ ] Sharing reports với người thân (chỉ read-only)
- [ ] Cloud sync (backup to cloud)
- [ ] OCR to auto-read meter readings from photos
- [ ] Budget tracking & forecasting
- [ ] Reminders for rent payment dates
- [ ] Integration with banking apps

---

## XI. FILE STRUCTURE (DỰ KIẾN)

```
lamnv_utils/addons/room_rental_expense/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── rental_room.py
│   ├── meter_reading.py
│   ├── room_invoice.py
│   ├── room_expense.py
│   ├── room_config.py
│   ├── room_history.py
│   ├── room_deposit.py
│   └── room_issue.py
├── views/
│   ├── rental_room_views.xml
│   ├── meter_reading_views.xml
│   ├── room_invoice_views.xml
│   ├── room_expense_views.xml
│   ├── room_config_views.xml
│   ├── room_history_views.xml
│   ├── room_deposit_views.xml
│   ├── room_issue_views.xml
│   ├── menu_views.xml
│   └── actions.xml
├── reports/
│   ├── invoice_template.xml
│   ├── report_summary.xml
│   ├── report_expenses.xml
│   └── report_meter_readings.xml
├── data/
│   ├── room_data.xml (sample data)
│   ├── room_config_data.xml (default prices)
│   └── demo_data.xml
├── security/
│   ├── ir_model_access.csv
│   └── room_security.xml
├── static/
│   ├── description/
│   │   ├── icon.png
│   │   └── index.html
│   ├── src/
│   │   ├── css/
│   │   └── js/
├── tests/
│   ├── __init__.py
│   ├── test_room.py
│   ├── test_invoice.py
│   ├── test_expense.py
│   └── test_calculations.py
└── README.md
```

---

## XII. NOTES

- Module này là **personal use** cho cá nhân bạn - không cần phức tạp
- Focus vào **tính tiền, theo dõi chi phí** hàng tháng
- Đơn giản, dễ sử dụng, không cần training
- Có thể expand để quản lý nhiều phòng nếu bạn ở nhiều chỗ
- UI tối ưu cho cả desktop và mobile
- Có thể export/backup dữ liệu dễ dàng

