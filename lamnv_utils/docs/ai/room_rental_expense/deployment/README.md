---
phase: deployment
title: Deployment Strategy
description: Define deployment process, infrastructure, and release procedures
---

# Deployment Strategy

## Infrastructure

Module này được triển khai như một custom addon Odoo:

- Application server: Odoo 19
- Database: PostgreSQL dùng chung với instance Odoo
- File storage: Odoo attachments cho ảnh phòng, ảnh công tơ, biên lai
- Public endpoint: cần publish route webhook Telegram nếu dùng tích hợp chat

Khuyến nghị tách môi trường:

- `dev`: phát triển và debug webhook nội bộ
- `staging`: test UAT, test cron, test Telegram
- `production`: dữ liệu thật

## Deployment Pipeline

### Build Process

1. Đồng bộ source code addon vào `addons_path`.
2. Khởi động Odoo với cấu hình module path phù hợp.
3. Update module:
   `odoo-bin -d <db> -u room_rental_expense --stop-after-init`
4. Kiểm tra assets backend nếu có thay đổi ở `static/src/js`.

### CI/CD Pipeline

- Kiểm tra lint Python/XML/JS nếu repo có pipeline chung.
- Chạy automated tests của module khi được bổ sung.
- Chỉ deploy production sau khi smoke test được các luồng:
  tạo chỉ số, tạo hóa đơn, thanh toán, cron, webhook Telegram.

## Environment Configuration

### Development

- Có thể dùng `ngrok` hoặc reverse proxy để expose webhook Telegram.
- Dùng bot Telegram riêng cho dev.
- Có thể giữ `telegram_allowed_chat_ids` hẹp cho 1-2 chat test.

### Staging

- Dùng DB sao chép hoặc dữ liệu seed.
- Kiểm tra secret token webhook và quyền route public.
- Xác thực PDF report và reminder activity hoạt động đúng.

### Production

- Bắt buộc cấu hình:
  - `telegram_webhook_secret`
  - `telegram_bot_token`
  - `telegram_allowed_chat_ids`
- Kiểm tra cron `Room Invoice Status Update` đang active.
- Thiết lập backup DB và filestore theo chuẩn Odoo production.

## Deployment Steps

1. Backup database và filestore.
2. Deploy source code mới lên server Odoo.
3. Chạy update module `room_rental_expense`.
4. Restart service Odoo nếu cần.
5. Kiểm tra:
   - mở menu module
   - tạo/sửa bản ghi phòng
   - tạo chỉ số và hóa đơn
   - in PDF
   - cron hoạt động
   - webhook Telegram phản hồi đúng

## Database Migrations

- Module hiện dùng ORM schema đơn giản, migration chủ yếu là `-u room_rental_expense`.
- Với thay đổi field compute/store hoặc SQL constraints, cần chạy trước trên staging.
- Nếu bổ sung SQL constraint cho `(room_id, reading_date)`, cần xử lý dữ liệu trùng trước khi upgrade.

## Secrets Management

- Không hard-code bot token hoặc webhook secret trong source code.
- Lưu secrets bằng `ir.config_parameter` và chỉ cấp quyền admin cấu hình.
- Nếu có pipeline hạ tầng riêng, có thể đồng bộ secrets từ vault vào DB trong bước bootstrap.

## Rollback Plan

- Rollback code về bản addon trước đó.
- Restore DB/filestore nếu upgrade dữ liệu gây lỗi không tương thích.
- Với sự cố chỉ liên quan Telegram, có thể tạm vô hiệu webhook hoặc xóa bot token mà không ảnh hưởng core nghiệp vụ Odoo.
