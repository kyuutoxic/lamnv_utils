---
phase: implementation
title: Implementation Guide
description: Technical implementation notes, patterns, and code guidelines
---

# Implementation Guide

## Development Setup

- Odoo target version: `19.0`
- Module path: `project/room_rental_expense`
- Python dependencies dùng từ runtime Odoo chuẩn và `python-dateutil`
- Module dependencies: `base`, `web`, `mail`, `base_setup`

Thiết lập cơ bản:

1. Đưa thư mục `project` vào `addons_path`.
2. Cập nhật app list.
3. Cài module `room_rental_expense`.
4. Nạp các cấu hình `ir.config_parameter` nếu muốn dùng Telegram hoặc thay giá mặc định.

Các `ir.config_parameter` quan trọng:

- `room_rental_expense.default_electric_price`
- `room_rental_expense.default_water_price`
- `room_rental_expense.default_wifi_price`
- `room_rental_expense.default_trash_fee`
- `room_rental_expense.default_parking_fee`
- `room_rental_expense.default_other_utilities_price`
- `room_rental_expense.reminder_days`
- `room_rental_expense.telegram_webhook_secret`
- `room_rental_expense.telegram_bot_token`
- `room_rental_expense.telegram_allowed_chat_ids`

## Code Structure

- `models/rental_room.py`: thực thể phòng và tổng hợp dữ liệu liên quan.
- `models/room_config.py`: giá tiện ích theo hiệu lực.
- `models/meter_reading.py`: chỉ số công tơ, validation, Telegram commands.
- `models/room_invoice.py`: hóa đơn, trạng thái, áp giá, reminder cron.
- `models/room_expense.py`: chi phí phát sinh.
- `models/room_deposit.py`: tiền cọc.
- `models/room_issue.py`: sự cố phòng.
- `models/room_history.py`: lịch sử phòng.
- `models/res_config_settings.py`: cấu hình Telegram trong Settings và action đăng ký command suggestions.
- `controllers/telegram_webhook.py`: webhook Telegram.
- `views/*.xml`: menu, list/form/search/report actions.
- `views/res_config_settings_views.xml`: giao diện cấu hình Telegram trong Settings.
- `reports/invoice_template.xml`: PDF invoice.
- `static/src/js/currency_widget.js`: widget format tiền/số.

## Implementation Notes

### Core Features

- Quản lý phòng:
  - `telegram_code` có unique SQL constraint.
  - `start_date <= end_date`.
  - `default_rent` được dùng làm mặc định khi tạo hóa đơn.

- Chỉ số công tơ:
  - Tự lấy chỉ số tháng trước bằng `_get_previous_reading`.
  - Chặn regression nếu số hiện tại nhỏ hơn số trước mà không bật cờ thay công tơ.
  - Khi thay công tơ, usage = `(replacement_last - previous) + current`.
  - Hỗ trợ manual override qua inverse field.
  - Không cho sửa/xóa bản ghi đã gắn hóa đơn.

- Hóa đơn:
  - `create()` inject giá trị mặc định, sinh sequence, áp config và sync liên kết chỉ số.
  - `write()` chặn sửa các trường lõi khi trạng thái khác `draft`.
  - Tổng tiền = `rent + electric + water + utilities + other - discount`.
  - Trạng thái cập nhật tự động theo tổng phải trả, số đã trả và hạn thanh toán.

- Telegram:
  - Chỉ nhận lệnh bắt đầu bằng `/`; nếu không có `/` thì trả về thông báo hướng dẫn.
  - Hỗ trợ các lệnh `/help`, `/reading`, `/inv`, `/show`, `/invoices`, `/readings`, `/paid`, `/pay`, `/unpaid`.
  - Tìm phòng qua `telegram_code`, `room_number`, `name`.
  - Upsert bản ghi chỉ số theo `(room_id, reading_date)` ở mức logic ứng dụng.
  - `/show` trả cả phần tổng quan hóa đơn và khối `Chi tiết` từ `manual_breakdown` để forward cho chủ nhà.
  - Có action trong `res.config.settings` để gọi Telegram `setMyCommands` và đăng ký command suggestions.
  - `/invoices` và `/readings` trả tối đa 10 bản ghi gần nhất theo phòng.

### Patterns & Best Practices

- Ưu tiên giữ `room.invoice` là nơi duy nhất quyết định giá trị hóa đơn cuối cùng.
- Khi bổ sung field tài chính mới cho hóa đơn, cần cập nhật:
  - `_compute_subtotal`
  - `_compute_total_amount`
  - `_compute_manual_breakdown`
  - PDF report nếu cần hiển thị
- Khi thêm lệnh Telegram mới, nên gắn vào `_dispatch_telegram_command` và viết hàm xử lý riêng.
- Khi thêm hoặc đổi lệnh Telegram, phải cập nhật:
  - `_dispatch_telegram_command`
  - `_get_telegram_help_message`
  - `res.config.settings._get_telegram_commands_payload`
  - `docs/ai/room_rental_expense/telegram/README.md`
- Với field bị khóa theo trạng thái, thêm vào `_locked_after_draft_fields` hoặc `_locked_fields_after_invoice`.

## Integration Points

- Telegram inbound:
  - Telegram gọi webhook Odoo.
  - Odoo xử lý message qua `meter.reading.process_telegram_message`.
  - Odoo gọi lại Telegram Bot API `sendMessage`.

- Telegram settings:
  - `res.config.settings` lưu `telegram_bot_token`, `telegram_webhook_secret`, `telegram_allowed_chat_ids` qua `config_parameter`.
  - Action `action_register_telegram_commands()` gọi Telegram `setMyCommands`.

- Odoo mail:
  - `room.invoice` dùng `mail.activity` để tạo nhắc thanh toán.

- Odoo reporting:
  - `action_print_invoice()` gọi action report `report_room_invoice_pdf`.

## Error Handling

- Validation nghiệp vụ chủ yếu dùng `ValidationError`.
- Telegram webhook luôn trả JSON; khi parse/validate thất bại sẽ trả `status: error` và message rõ ràng.
- Gửi phản hồi Telegram thất bại chỉ được log, không rollback luồng xử lý chính.

## Performance Considerations

- Các tổng trên `rental.room` là stored compute, phù hợp cho list/kanban.
- `_get_previous_reading` hiện dựa vào recordset/filter Python; nếu dữ liệu tăng lớn nên cân nhắc search domain + index.
- Upsert Telegram hiện tìm kiếm theo phòng và ngày; nếu lưu lượng lớn nên thêm SQL constraint/index tương ứng.

## Security Notes

- Webhook Telegram là route public, vì vậy secret token và allowlist chat ID là lớp bảo vệ bắt buộc khi triển khai thực tế.
- Toàn bộ model đang cho phép CRUD với `base.group_user`; nếu dùng cho nhiều người cần bổ sung record rules hoặc nhóm riêng.
- Ảnh biên lai, ảnh phòng và ảnh công tơ được lưu dưới dạng attachment của Odoo.
