---
title: AI Documentation Index
description: Module-oriented AI docs index
---

# AI Documentation

Tài liệu AI được tổ chức theo từng module để tránh trùng tên file và dễ mở rộng khi repo có thêm addon mới.

## Module Catalog

### `room_rental_expense`

- Mục đích: quản lý phòng trọ cá nhân, chỉ số điện nước, hóa đơn, chi phí phát sinh, tiền cọc, sự cố và nhắc thanh toán.
- Odoo version: `19.0`
- Module path: `project/room_rental_expense`
- Core models:
  - `rental.room`
  - `meter.reading`
  - `room.invoice`
  - `room.config`
  - `room.expense`
  - `room.deposit`
  - `room.issue`
  - `room.history`
- Main features:
  - quản lý thông tin phòng và chủ phòng
  - cấu hình giá điện, nước và tiện ích theo ngày hiệu lực
  - ghi chỉ số công tơ, kể cả thay công tơ và nhập tay mức tiêu thụ
  - tạo hóa đơn từ chỉ số công tơ và theo dõi thanh toán
  - cron cập nhật quá hạn và tạo reminder activity
  - webhook Telegram để nhập chỉ số và thao tác hóa đơn nhanh
- Technical notes:
  - phụ thuộc `base`, `web`, `mail`
  - có widget JS format tiền VND trong backend
  - dùng `ir.config_parameter` cho giá mặc định và cấu hình Telegram

## Modules

- `room_rental_expense`
  - [Module Overview](./room_rental_expense/README.md)
  - [Requirements](./room_rental_expense/requirements/README.md)
  - [Design](./room_rental_expense/design/README.md)
  - [Implementation](./room_rental_expense/implementation/README.md)
  - [Testing](./room_rental_expense/testing/README.md)
  - [Planning](./room_rental_expense/planning/README.md)
  - [Deployment](./room_rental_expense/deployment/README.md)
  - [Monitoring](./room_rental_expense/monitoring/README.md)
  - [Telegram Guide](./room_rental_expense/telegram/README.md)
