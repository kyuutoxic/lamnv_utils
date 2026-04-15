---
phase: testing
title: Testing Strategy
description: Define testing approach, test cases, and quality assurance
---

# Testing Strategy

## Test Coverage Goals

- Mục tiêu cho module này: bao phủ toàn bộ luồng nghiệp vụ cốt lõi và các validation quan trọng.
- Ưu tiên integration tests cho model methods vì phần lớn logic nằm trong ORM Odoo.
- Bổ sung manual test cho UI form/list, report PDF và Telegram webhook.

## Unit Tests

### `rental.room`

- [ ] Kiểm tra lỗi khi `end_date < start_date`.
- [ ] Kiểm tra unique `telegram_code`.
- [ ] Kiểm tra `_get_active_config()` trả đúng cấu hình gần nhất theo ngày tham chiếu.
- [ ] Kiểm tra các tổng `total_invoiced`, `total_paid`, `total_remaining`, `total_expenses`.

### `room.config`

- [ ] Không cho phép giá trị âm.
- [ ] Không cho phép trùng `(room_id, effective_date)`.
- [ ] `name` được compute đúng theo phòng và ngày hiệu lực.

### `meter.reading`

- [ ] Tự lấy `electric_previous` và `water_previous` từ kỳ trước.
- [ ] Chặn số hiện tại nhỏ hơn số trước khi không thay công tơ.
- [ ] Tính usage đúng khi thay công tơ.
- [ ] Tính usage đúng khi manual override.
- [ ] Không cho sửa/xóa bản ghi đã gắn `invoice_id`.
- [ ] Parse đúng hai định dạng dữ liệu của `/reading`.
- [ ] Báo lỗi khi Telegram message sai format hoặc sai ngày.
- [ ] Tin nhắn không bắt đầu bằng `/` chỉ trả về thông báo hướng dẫn.
- [ ] `/invoices` trả đúng danh sách hóa đơn gần nhất theo phòng.
- [ ] `/readings` trả đúng danh sách chỉ số gần nhất theo phòng.

### `room.invoice`

- [ ] `create()` tự set `invoice_number`, `invoice_date`, `invoice_month`, `due_date`.
- [ ] Áp đúng `default_rent` từ phòng nếu chưa nhập.
- [ ] Áp đúng `room.config` hoặc fallback `ir.config_parameter`.
- [ ] Tính đúng `electric_amount`, `water_amount`, `subtotal`, `total_amount`, `remaining_amount`.
- [ ] Chặn sửa trường lõi sau khi rời `draft`.
- [ ] Chặn liên kết chỉ số khác phòng hoặc khác tháng.
- [ ] Chuyển trạng thái đúng cho các case `draft/pending/partially_paid/paid/overdue/canceled`.
- [ ] `cron_update_overdue_status()` cập nhật overdue và tạo `mail.activity`.
- [ ] `manual_breakdown` hiển thị đúng để dùng lại trong phản hồi Telegram `/show`.

### `res.config.settings`

- [ ] Lưu đúng `telegram_bot_token`, `telegram_webhook_secret`, `telegram_allowed_chat_ids`.
- [ ] `action_register_telegram_commands()` gọi đúng Telegram `setMyCommands`.
- [ ] Báo lỗi rõ ràng khi thiếu bot token hoặc Telegram API trả lỗi.

## Integration Tests

- [ ] Tạo phòng, cấu hình giá, chỉ số công tơ, rồi tạo hóa đơn từ `action_create_invoice`.
- [ ] Cập nhật `meter_reading_id` trên hóa đơn và xác nhận đồng bộ hai chiều `invoice_id`.
- [ ] Kiểm tra chỉ một hóa đơn được gắn với một chỉ số công tơ.
- [ ] Kiểm tra upsert chỉ số qua Telegram cho bản ghi mới và bản ghi đã tồn tại.
- [ ] Kiểm tra các lệnh `/reading`, `/inv`, `/show`, `/invoices`, `/readings`, `/paid`, `/pay`, `/unpaid`.
- [ ] Kiểm tra action đăng ký command suggestions trong Settings.

## End-to-End Tests

- [ ] Người dùng tạo phòng mới, khai báo chủ phòng và giá thuê mặc định.
- [ ] Người dùng tạo cấu hình giá có hiệu lực từ một ngày cụ thể.
- [ ] Người dùng ghi chỉ số tháng mới và tạo hóa đơn ngay từ form chỉ số.
- [ ] Người dùng thanh toán một phần rồi thanh toán đủ, trạng thái và số còn lại cập nhật chính xác.
- [ ] Người dùng in PDF hóa đơn.
- [ ] Telegram gửi chỉ số và tạo hóa đơn thành công với secret đúng.
- [ ] Telegram `/show` trả được phần `Chi tiết` để forward cho chủ nhà.

## Test Data

- Phòng mẫu có `telegram_code`, `default_rent`, landlord info.
- Ít nhất hai cấu hình giá với `effective_date` khác nhau.
- Hai kỳ chỉ số liên tiếp để kiểm tra previous reading.
- Dữ liệu hóa đơn với các case: chưa trả, trả một phần, đã trả, quá hạn.

## Test Reporting & Coverage

- Hiện repo chưa có test file cho module này.
- Khi bổ sung test, nên đặt trong `project/room_rental_expense/tests/`.
- Cần chạy test qua Odoo test runner với database riêng cho module.

## Manual Testing

- [ ] Kiểm tra form chỉ số công tơ ẩn/hiện đúng field khi thay công tơ.
- [ ] Kiểm tra readonly đúng khi chỉ số đã có hóa đơn.
- [ ] Kiểm tra hóa đơn readonly đúng sau khi xác nhận.
- [ ] Kiểm tra widget `vnd_currency` và `number_format` hiển thị đúng ở list/form/kanban.
- [ ] Kiểm tra PDF invoice hiển thị đủ breakdown.
- [ ] Kiểm tra menu báo cáo mở được pivot/graph/list.
- [ ] Kiểm tra màn hình Settings hiển thị đúng các field Telegram và bấm được nút đăng ký lệnh.

## Performance Testing

- [ ] Seed dữ liệu nhiều tháng chỉ số và hóa đơn để đánh giá tốc độ mở list view.
- [ ] Đo thời gian webhook Telegram khi xử lý liên tục nhiều tin nhắn.
- [ ] Theo dõi cron với tập dữ liệu hóa đơn quá hạn lớn hơn bình thường.

## Bug Tracking

- Theo dõi riêng các lỗi liên quan đến:
  - sai công thức usage khi thay công tơ
  - lệch giá áp dụng theo `effective_date`
  - trạng thái hóa đơn không đồng bộ sau thanh toán
  - webhook Telegram nhận sai chat hoặc secret
  - slash command Telegram không khớp help message hoặc command suggestions
