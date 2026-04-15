---
phase: monitoring
title: Monitoring & Observability
description: Define monitoring strategy, metrics, alerts, and incident response
---

# Monitoring & Observability

## Key Metrics

### Business Metrics

- Số phòng đang quản lý.
- Số chỉ số công tơ được ghi theo tháng.
- Số hóa đơn theo trạng thái `draft/pending/partially_paid/paid/overdue`.
- Tổng số tiền phải thu, đã thu, còn lại theo tháng.
- Tổng chi phí phát sinh theo danh mục.

### Error Metrics

- Số webhook Telegram bị từ chối do `invalid_secret`.
- Số message Telegram lỗi parse/validation.
- Số lần gửi phản hồi Telegram thất bại.
- Số hóa đơn chuyển `overdue` mỗi ngày.

### Operational Metrics

- Thời gian xử lý webhook Telegram.
- Thời gian chạy cron cập nhật trạng thái hóa đơn.
- Số lượng `mail.activity` nhắc thanh toán được tạo.

## Monitoring Tools

- Odoo server logs cho application logs.
- PostgreSQL monitoring cho database health.
- Reverse proxy/web server logs cho HTTP webhook.
- Nếu có hạ tầng đầy đủ: APM và log aggregation như Prometheus/Grafana, ELK, Datadog.

## Logging Strategy

- Log cảnh báo khi webhook Telegram dùng secret sai.
- Log exception khi gọi Telegram Bot API thất bại.
- Không log bot token, secret hoặc nội dung nhạy cảm ngoài mức cần thiết để debug.
- Nên bổ sung correlation theo `invoice_number`, `room_id`, `chat_id` nếu mở rộng logging sau này.

## Alerts & Notifications

### Critical Alerts

- Webhook Telegram trả lỗi 5xx liên tục trong production.
- Cron hóa đơn không chạy quá `24 giờ`.
- Tỷ lệ hóa đơn `overdue` tăng bất thường sau một kỳ release.

### Warning Alerts

- Có nhiều request webhook bị `403 invalid_secret`.
- Telegram reply failures tăng đột biến.
- Số `mail.activity` reminder không được tạo dù có hóa đơn sắp đến hạn.

## Dashboards

- Dashboard tài chính:
  - tổng tiền hóa đơn theo tháng
  - đã thanh toán / còn lại
  - số hóa đơn quá hạn
- Dashboard vận hành:
  - số request webhook
  - lỗi webhook
  - thời gian cron
- Dashboard dữ liệu:
  - chỉ số điện/nước theo phòng và tháng
  - chi phí phát sinh theo danh mục

## Incident Response

### Incident Process

1. Xác định lỗi thuộc dữ liệu nghiệp vụ, webhook Telegram hay cron.
2. Kiểm tra logs Odoo và trạng thái route public.
3. Với lỗi Telegram, xác minh secret, bot token, allowed chat IDs và khả năng outbound tới Telegram API.
4. Với lỗi hóa đơn, kiểm tra liên kết `meter_reading_id`, `applied_config_id`, `due_date`, `paid_amount`.
5. Khắc phục và chạy smoke test các luồng chính.

## Health Checks

- Health check ứng dụng Odoo tổng quát của instance.
- Smoke check module:
  - mở được menu `Quản Lý Phòng Trọ`
  - tạo được chỉ số mới
  - tạo được hóa đơn từ chỉ số
  - cron đang active
  - webhook Telegram nhận và phản hồi message test hợp lệ
